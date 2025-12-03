import pandas as pd
import dotenv
import os
import psycopg
from psycopg import sql
import networkx as nx

"""This is the logic used during analysis and transformation
    of the scraped data, used to create the graph object,
    taken from the jupyter notebooks and functionalised
    """


def get_subreddit_comment_count():
    dotenv.load_dotenv(override=True)
    db_string = os.getenv("DB_STRING") or "localhost"
    conn = psycopg.connect(
        db_string,
        autocommit=True,
    )
    # select db
    schema = "test"
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("SET search_path TO {}").format(sql.Identifier(schema))
        )
    query = """
    SELECT subreddit, COUNT(*) as comment_count
    FROM COMMENTS
    GROUP BY subreddit"""
    subreddit_comments_count = pd.read_sql(
        query,
        conn,
    )
    subreddit_comments_count.to_csv(
        "presentation/data/subreddit_comment_counts.csv", index=False
    )


def get_edge_data():

    dotenv.load_dotenv(override=True)
    db_string = os.getenv("DB_STRING") or "localhost"
    conn = psycopg.connect(
        db_string,
        autocommit=True,
    )
    # select db
    schema = "test"
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("SET search_path TO {}").format(sql.Identifier(schema))
        )

    query = """
    WITH authors_subreddits AS (SELECT DISTINCT author, subreddit FROM COMMENTS
    ORDER BY author)
    SELECT
    a_s.author,
    string_agg(a_s.subreddit, ',') AS subreddit_list
    FROM authors_subreddits a_s
    GROUP BY a_s.author
    """

    redditors_with_subreddits = pd.read_sql(query, conn)
    ##
    shared_commenters_hash = {}
    for index, row in redditors_with_subreddits.iterrows():
        subreddits = row["subreddit_list"].split(",")
        for i in range(len(subreddits)):
            for j in range(i + 1, len(subreddits)):
                pair = tuple(sorted([subreddits[i], subreddits[j]]))
                shared_commenters_hash[pair] = (
                    shared_commenters_hash.get(pair, 0) + 1
                )
    # make df
    edge_weights = pd.DataFrame(
        shared_commenters_hash.items(),
        columns=["subreddit_pair", "shared_commenter_count"],
    )
    # sort rows by first then second subreddit alphabetically
    edge_weights = (
        edge_weights.assign(
            sub1=edge_weights["subreddit_pair"].apply(lambda t: t[0]),
            sub2=edge_weights["subreddit_pair"].apply(lambda t: t[1]),
        )
        .sort_values(["sub1", "sub2"])
        .drop(columns=["sub1", "sub2"])
        .reset_index(drop=True)
    )
    # cleaning and filtering
    cleaned_edges = edge_weights[
        edge_weights["subreddit_pair"].apply(
            lambda x: x[0].startswith("r/") and x[1].startswith("r/")
        )
    ]
    filtered_edges = cleaned_edges[
        cleaned_edges["shared_commenter_count"] >= 5
    ]
    filtered_edges.to_csv(
        "presentation/data/subreddit_edge_weights_cleaned_filtered.csv",
        index=False,
    )


def make_graph():
    edge_df = pd.read_csv(
        "presentation/data/subreddit_edge_weights_cleaned_filtered.csv"
    )
    unformatted_edges = edge_df.values.tolist()
    # make edge object
    edges = []
    for pair_str, weight in unformatted_edges:
        subpair = tuple(pair_str.strip("()").replace("'", "").split(", "))
        edges.append((subpair, weight))
    # get list of all subs
    subs_set = set()
    for (sub1, sub2), weight in edges:
        subs_set.add(sub1)
        subs_set.add(sub2)
    subs = list(subs_set)
    G = nx.Graph()
    G.add_nodes_from(subs)
    for (sub1, sub2), weight in edges:
        G.add_edge(sub1, sub2, weight=weight)
    # enrich with comment_count attribute
    subreddit_comment_counts_df = pd.read_csv(
        "presentation/data/subreddit_comment_count.csv"
    )
    comment_count_dict = dict(subreddit_comment_counts_df.values)
    for subreddit, count in comment_count_dict.items():
        if subreddit in G.nodes():
            G.nodes[subreddit]["comment_count"] = count
    # ensure attributes are correct type for gephi
    for node, data in G.nodes(data=True):
        data["comment_count"] = int(data["comment_count"])

    for u, v, data in G.edges(data=True):
        data["weight"] = float(data["weight"])
    nx.write_gexf(G, "../data/subreddit_network.gexf")


if __name__ == "__main__":
    get_subreddit_comment_count()
    get_edge_data()
    make_graph()
