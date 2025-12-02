import streamlit as st
import pandas as pd

st.header("Analysis")

st.markdown(
    """
    After gathering a substantial amount of data, 1.3million comments from 33,000 subreddits.
    I set out to analyse the structure of the communities I had scraped.
"""
)

st.markdown(
    """
    ## Methodology-
    I opted to use the number of shared commenters (i.e. redditors who had commented in both subreddits) 
    as a measure of connectedness between communities.
"""
)

st.warning(
    """as the original ETL processes only took vertical slices of a single comment/thread/subreddit and not at commenters.
    The data may have been sparse in terms of commenter overlap"""
)

st.success(
    """
    To flesh out the data I wrote a script which given a redditor/list of redditors, 
    would fetch the top *n* posts from that redditor.

    To specifically find connections I wrote a script which would recursively follow subreddits,
    taking the top redditors from the subreddit, examining their comments, 
    scraping them and then applying the same function to the subreddits those comments were posted to.
"""
)

st.warning(
    """
    the recursive expansion of the dataset did work although two main problems were encountered
    1. Recursive function calls can be slow and blow up fast on large datasets, 
        so the depth of the recursion was limited
    2. The algorithm was prone to falling down rabbit holes rather than finding more surprising connections. 
        
        E.g. following a redditor to r/Canada->r/Ontario->r/Quebecois->r/Montreal->r/Quebec 
"""
)

st.divider()

st.markdown(
    """
    ## Transformation
    #### Goal - A table consisting of a column of subreddit pairs and a column of their shared commenter count.
    
    To get a measure of who commented where I used the postgrest function `string_agg` to produce a comma separated
    list of subreddits a user had commented in.
    ```sql
    WITH authors_subreddits AS (SELECT DISTINCT author, subreddit FROM COMMENTS
    ORDER BY author)
    SELECT 
    a_s.author,
    string_agg(a_s.subreddit, ',') AS subreddit_list
    FROM authors_subreddits a_s
    GROUP BY a_s.author 
    ```

"""
)

redditors_with_subreddits = pd.read_csv(
    "presentation/data/redditor_subreddit_list.csv"
)

st.write(redditors_with_subreddits.head(5))

st.markdown(
    """
    A dictionary was then produced with the pairs and their shared subredditor count.
    ```python
    shared_commenters_hash = {}
    for index, row in redditors_with_subreddits.iterrows():
        subreddits = row['subreddit_list'].split(',')
        for i in range(len(subreddits)):
            for j in range(i + 1, len(subreddits)):
                pair = tuple(sorted([subreddits[i], subreddits[j]]))
                shared_commenters_hash[pair] = shared_commenters_hash.get(pair, 0) + 1
    ```
    ```json
    {('r/Atlanta', 'r/Blacksmith'): 1,
    ('r/Atlanta', 'r/Braves'): 1,
    ('r/Atlanta', 'r/BuyItForLife'): 1,
    ('r/Atlanta', 'r/civilengineering'): 1,
    ('r/Atlanta', 'r/Damnthatsinteresting'): 1,
    ('r/Atlanta', 'r/dank_meme'): 1,
    ('r/Atlanta', 'r/dankmemes'): 2,
    ...}
    ```
    
    This was then loaded as a pandas dataframe and 
    sorted alphabetically on the first and second subreddit names.

    """
)
st.divider()

st.markdown(
    """
    The data was then filtered to remove subreddit pairs with less than a threshold number of 
    commenters.
"""
)
st.success(
    """
    removing pairs with less than 5 commenters cut the table from **367,000** rows to **117,000**
"""
)

st.divider()

st.markdown(
    """
    ## Network Analysis

    The form of the data lends itself to analysis as a network graph. The graph data was made using networkx (**nx**).
    first the edge weight data was loaded into a pd dataframe and then transformed for pythonic transformation  

    ```python
    edge_df = pd.read_csv('../data/subreddit_edge_weights_cleaned_filtered.csv')
    unformatted_edges = edge_df.values.tolist()
    edges = []
    for pair_str, weight in unformatted_edges:
        subpair = tuple(pair_str.strip("()").replace("'", "").split(", "))
        edges.append((subpair, weight))
    ```

    ```python
    G = nx.Graph()
    G.add_nodes_from(subs)
    for (sub1,sub2), weight in edges:
        G.add_edge(sub1, sub2, weight=weight)
    ```
    """
)
with st.container(horizontal=True):
    st.metric(label="Nodes", value="7,889")
    st.metric(label="Edges", value="117,351")

st.markdown(
    """
    The data was then enriched by adding a 'comment_count' atribute to each node,
      reflecting how many total comments the subreddit had.
    ```python
    for subreddit, count in comment_count_dict.items():
        if subreddit in G.nodes():
            G.nodes[subreddit]['comment_count'] = int(count)
    ```
    finally the data was written to a graph format   
    ```python
    nx.write_gexf(G, '../data/subreddit_network.gexf')
    ```
"""
)

with st.expander("Don't do big data on a potato"):
    st.markdown(
        """
    I had initially planned to do the graph analysis natively through streamlit, but after researching
    I discovered streamlit's graphing functionality was somewhat limited for larger graphs.

    At first I opted to use the python pyvis module, which actually uses javascript for the visualisation. But 
    pyvis immediately ran into difficulties with memory...
    """
    )
    st.image("presentation/assets/pyvis_time.png")
    st.image("presentation/assets/pyvis_time_big.png", width=500)

st.divider()

st.markdown(
    """
    The graph was imported into the open source network analysis software [Gephi](https://gephi.org/)
"""
)
