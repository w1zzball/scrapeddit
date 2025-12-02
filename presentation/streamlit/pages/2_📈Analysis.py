import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_image_zoom import image_zoom
from PIL import Image


# @st.dialog("zoomable")
def zoomable(img_path):
    image = Image.open(img_path)
    return image_zoom(image, keep_resolution=True, mode="dragmove", size=704)


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

    The graph trimmed to exclude nodes with under 200 comments and then allowed to expand within
    constraints defined by the edge weights using gephi's
    ForceAtlas2 algorithm until it had settled. After which a classification algorithm <a href=#footer>[1]</a> was run to 
    partition the graph's topology into "modularity classes", henceforce referred to as 'communities'. This is what the first analysis produced. 
""",
    unsafe_allow_html=True,
)
st.success(
    """
    The data included many Isolated/niche communities, 13% of nodes make up 50% of all edges
"""
)

with st.expander("first attempt"):
    st.markdown(
        """
        my first attempt ran into trouble as there were too few categories, for instance, gaming, anime 
        and most films were all grouped into one huge cohort. 
    """
    )
    if "show_p1_labels" not in st.session_state:
        st.session_state.show_p1_labels = True

    if st.button("Toggle labels", key="p1"):
        st.session_state.show_p1_labels = not st.session_state.show_p1_labels

    filename = f"presentation/assets/graphs/whole_graph_{'no' if not st.session_state.show_p1_labels else ''}labels.png"
    st.image(filename)

st.markdown(
    """
    after experimenting with partition parameters I found settings which split the data into a 
    few large communities with dominant themes.
"""
)

partition2_whole_images = [
    "presentation/assets/graphs/partition2/whole_graph_nolabels.png",
    "presentation/assets/graphs/partition2/whole_graph_extralargefont.png",
]
if "show_p2_labels" not in st.session_state:
    st.session_state.show_p2_labels = True

if st.button("Toggle labels", key="p2"):
    st.session_state.show_p2_labels = not st.session_state.show_p2_labels
zoomable(partition2_whole_images[st.session_state.show_p2_labels == True])

# treemap data

community_data = {
    "category": [
        "Cats, Pets, Home",
        "General, Q/A",
        "Anime, Memes, Youth",
        "Gaming",
        "TV / Film / Fantasy / Sports",
        "42 Other communities",
    ],
    "proportion of subreddits": [36.29, 14.2, 8.78, 4.76, 3.49, 32.48],
}

community_df = pd.DataFrame(community_data)

custom_colours = {
    "Cats, Pets, Home": "#00FFFF",
    "General, Q/A": "#FF741E",
    "Anime, Memes, Youth": "#25FE00",
    "Gaming": "#FF97FF",
    "TV / Film / Fantasy / Sports": "#FCFF32",
    "42 Other communities": "#999999",
}

fig = px.treemap(
    community_df,
    path=["category"],
    values="proportion of subreddits",
    color="category",
    color_discrete_map=custom_colours,
)
fig.update_traces(textinfo="label+value")
st.plotly_chart(fig)

cats, general, anime, gaming, tv = st.tabs(community_data["category"][:-1])

with cats:
    st.markdown(
        """
    This community is dominated by subreddits about cats, pets, fashion and home improvement.
    Dominated by cat themed subreddits, with a large contingent of home decor and fashion 
    subreddits. With some gaming subreddits creeping upwards towards the larger gaming community.
    """
    )
    zoomable("presentation/assets/graphs/partition2/cats_1_largefont.png")

with general:
    st.markdown(
        """
    This community is made up of general interest and question/answer subreddits.
    The generality of this community is shown by it's large spread and central location.
    It also has subsections e.g. writing questions and gendered subreddits
    """
    )
    zoomable(
        "presentation/assets/graphs/partition2/general_ask_15_largefont.png"
    )

with anime:
    st.markdown(
        """
    This community is dominated by subreddits about anime, memes and youth culture.
    The lower left portion being mostly internet/meme culture. This community also has large
    overlap with gaming.
    """
    )
    zoomable(
        "presentation/assets/graphs/partition2/anime_memes_youth_17_largefont.png"
    )

with gaming:
    st.markdown(
        """
    This community is dominated by gaming subreddits. The lack of outliers indicates
    that the degree of relation between gaming subreddits is very high.
    
    """
    )
    zoomable("presentation/assets/graphs/partition2/gaming_11_largefont.png")

with tv:
    st.markdown(
        """
    This large and disperate community is centred on subreddits about TV, film, fantasy and sports.
    The loose connection between some of these topics is suggested by the spread out nature of the graph.
    
    """
    )
    zoomable(
        "presentation/assets/graphs/partition2/film_sports_fantasy_30_extralargefont.png"
    )

st.markdown(
    """
    #### Interesting observations from smaller communities
"""
)

diy, genx, mtg, uk, programming = st.tabs(
    ["DIY", "GenX", "Magic the Gathering", "UK", "Programming"]
)

with diy:
    st.markdown(
        """
    The DIY subreddits share a community with guitar,lawncare and urban exploration subreddits
    """
    )
    zoomable(
        "presentation/assets/graphs/partition2/smaller_communities/DIY.png"
    )

with genx:
    st.markdown(
        """
    The GenX subreddit has many music related subreddits in its community
    r/Cd_collectors. It also has r/dogs
    """
    )
    zoomable(
        "presentation/assets/graphs/partition2/smaller_communities/GenX.png"
    )

with mtg:
    st.markdown(
        """
    The Small number of card game Magic the Gathering subreddits share a community
    with Dungeons and Dragons subreddits and groups dedicated to game dev and python programming
    """
    )
    zoomable(
        "presentation/assets/graphs/partition2/smaller_communities/MTG_python.png"
    )

with uk:
    st.markdown(
        """
    The UK groups share a community with most football related subreddits
    """
    )
    zoomable(
        "presentation/assets/graphs/partition2/smaller_communities/UK.png"
    )

with programming:
    st.markdown(
        """
    The community which contains general programming and linux subreddits 
    also contains the startrek and stargate groups and groups related to the
    Sanfransisco and New York areas
    """
    )
    zoomable(
        "presentation/assets/graphs/partition2/smaller_communities/programming.png"
    )


st.markdown(
    """
    <footer id="footer">
    <small>[1]
    Vincent D Blondel, Jean-Loup Guillaume, Renaud Lambiotte, Etienne Lefebvre, Fast unfolding of communities in large networks, in Journal of Statistical Mechanics: Theory and Experiment 2008 (10), P1000
    </small>
    </footer>
""",
    unsafe_allow_html=True,
)
