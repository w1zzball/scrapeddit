import streamlit as st

with st.sidebar.container():
    with st.expander("how to read"):
        st.success("Highlights in Green")
        st.warning("Roadblocks in Yellow")
        st.expander("Asides in Accordions")

st.header("Design")

st.markdown(
    """
    As the PRAW API exposes the full comment thread from a submission
    object by means of a `replace_more()` method, which populates a
    comment tree scraping entire threads becomes a matter of getting
      a submission and following along the comments. As PRAW also allows
    for getting the top **N** submissions from a subreddit this
    could easily be extended to scraping entire subreddits.
    """
)

# UX/UI

st.markdown(
    """
    ### UX/UI   
    Given the breadth of choice available in terms of both the granularity and
    sheer amount of data available on reddit. I opted to build a tool
    which gave the user control over what to extract.
    To this end I created a command line interface employing the
    `prompt_toolkit` library,
    """
)

st.success(
    """this library also allows for nice
    quality of life features like history and autocomplete
    for free.
    """
)

with st.container(horizontal_alignment="center"):
    st.image("presentation/assets/prompt_toolkit_features.png")

st.divider()

# parallelism
st.markdown(
    """
    ### Parallelism   
"""
)
st.warning(
    """initially the reddit API was called sequentially,
         each Get request having to wait for the previous to complete
        this resulted in long extraction times"""
)

st.markdown(
    """
    The sequential extraction was replaced by a multithreaded approach
    where a number of requests were dispatched at once. The number of 'workers'
    being supplied by the user (defaulting to 5)
    """
)

st.markdown(
    """
    The extracted data is transformed, removing unnecessary information
      such as duplicate or derived fields, unnecessary or volatile statistics
      (e.g. the post's controversiality). Before being loaded into a remote
     database hosted by [Aiven](https://aiven.io/)
    """,
    unsafe_allow_html=True,
)

with st.expander("A cautionary tale"):
    st.markdown(
        """
        after achieving a double digit times speedup with parrelelism I left the extraction
        running overnight scraping the top 1000 threads in the top 1000
         subreddits upon waking the next morning I had a respectable 2.3 Million comments/submissions scraped.
           
        then I opened my email
    """
    )
    st.image("presentation/assets/server_low_on_space.png")
    st.image("presentation/assets/server_in_read_only_mode.png")
    st.image("presentation/assets/server_deleted.png")

st.divider()
# invocation

st.markdown(
    """
    ### Automation   
    To enable automation the program can recieve arguments from the command line rather
      than through the prompt, this along with a wrapper program allows for bulk scraping
      with the ability to pause and resume scrapes via lists of scraped / to scrape subreddits.     
"""
)

st.success(
    """
    Any arguments after the file are passed directly to the prompt
      handler as if user input so no extra logic is necessary.
      """
)

st.markdown(
    """
      ```python
      if len(sys.argv) < 2 or cli_input_executed:
                user_input = session.prompt(
                    "scrapeddit> ",
                    bottom_toolbar=bottom_toolbar,
                    auto_suggest=AutoSuggestFromHistory(),
                    wrap_lines=True,
                ).strip()
                if not user_input:
                    continue
            else:
                # CLI invocation
                user_input = " ".join(sys.argv[1:]).strip()
                cli_input_executed = True
                if not user_input:
                    continue
      ```
"""
)

st.warning(
    """
    Reddit uses a dynamic throttling/request limit policy which means the 
    amount or GET requests a post can accept varies dependant on the 
    post's popularity. The upshot of this is that trying to scrape the top
    posts of very popular subreddits often results in a http 429 error, meaning too 
    many requests have been made on that resource recently. There is seemingly no 
    workaround for this, and to avoid bottlenecks the program simply logs it 
    and continues.
"""
)

st.divider()

st.markdown(
    """
    ### Modularity   
    Because of the multiple different types of extraction 
    the tool supports and the similar nature of arguments they 
    take, the tool uses a modular approach to parsing and calling functions
    most functions are read from a supporting datastructure which 
    defines both their prompt characteristics (help text etc) and their arguments. 
"""
)

st.success("This makes creating and updating functions much simpler")

st.markdown(
    """
    ```json
    prompt_data = {
    "scrape": {
        "base": {
            "targets": (),
            "desc": (
                "Usage: <b>scrape &lt;target&gt; &lt;id_or_url&gt;</b>\\n"
                " [--overwrite|-o] [--limit N] "
                "[--threshold N] [--max-workers N]"
            ),
            "func": None,
        },
        "error": {
            "targets": (),
            "desc": (
                "Error: Invalid scrape command. "
                "Unknown scrape target. Use thread, submission, "
                "comment, redditor or subreddit"
            ),
            "func": None,
        },
        "thread": {
            "targets": ("thread", "t", "entire", "entire_thread"),
            "desc": (
                "thread: scrape submission + comments. Flags: \\n"
                "--overwrite/-o, --limit N (None=all), --threshold N"
            ),
            "func": scrape_entire_thread,
        },
    ```
"""
)

st.divider()

st.markdown(
    """
    #### A note about nonexistent comments
"""
)

st.warning(
    """
    Comments that have been deleted / removed by moderators, or comments who's authors have 
    deleted their account will by still be scraped as these data are still potentially useful.
    Such comments have a body of `[deleted]` or an Author of `None` respectively. 
"""
)

st.divider()

st.markdown(
    """
    ### Schema Design
"""
)


st.markdown(
    """
    #### Comments

|Column|Type|Constraints|Default|Description|
|---|---|---|---|---|
|`name`|TEXT|PRIMARY KEY|–|Fully-qualified Reddit ID (e.g., `t1_nn428xe`)|
|`author`|TEXT||–|Comment author username|
|`body`|TEXT||–|Plain text body of the comment|
|`created_utc`|TIMESTAMPTZ|NOT NULL|–|UTC timestamp of creation|
|`edited`|BOOLEAN||FALSE|Whether the comment was edited|
|`ups`|INT||0|Upvote count|
|`parent_id`|TEXT||–|ID of the parent comment or submission|
|`submission_id`|TEXT|NOT NULL|–|ID of the submission this comment belongs to|
|`subreddit`|TEXT|NOT NULL|–|Name of the subreddit|
#### Submissions (original post of the thread)
| Column        | Type        | Constraints | Default | Description                             |
| ------------- | ----------- | ----------- | ------- | --------------------------------------- |
| `name`        | TEXT        | PRIMARY KEY | –       | Reddit ID (e.g., `t3_abcd123`)          |
| `author`      | TEXT        |             | –       | Submission author username              |
| `title`       | TEXT        |             | –       | Title of the submission                 |
| `selftext`    | TEXT        |             | –       | Submission body (for text posts)        |
| `url`         | TEXT        |             | –       | URL (for link posts)                    |
| `created_utc` | TIMESTAMPTZ | NOT NULL    | –       | UTC timestamp of creation               |
| `edited`      | BOOLEAN     |             | FALSE   | Whether the submission was edited       |
| `ups`         | INT         |             | 0       | Upvote count                            |
| `subreddit`   | TEXT        | NOT NULL    | –       | Name of the subreddit                   |
| `permalink`   | TEXT        | NOT NULL    | –       | Permanent Reddit URL for the submission |

"""
)

with st.container(horizontal=True):
    with st.container(border=True):
        st.page_link("Overview.py", label="Overview", width="stretch")
    with st.container(border=True):
        st.page_link(
            "pages/2_📈Analysis.py", label="Analysis", width="stretch"
        )
