import streamlit as st

st.markdown(
    '<h1 style="color:#FF4500"><b>Scrapeddit</b></h1>', unsafe_allow_html=True
)
with st.container(horizontal_alignment="center", horizontal=True):
    st.markdown(
        """
        <style>
        .orange-button {
            background-color: #FF4500;
            color: white;
            border: none;
            padding: 5px 10px;
            text-align: center;
            border-radius: 10px;
            }
        .subheader {
            margin: 0 auto;
            font-size: 20px;
            font-weight: bold;
            }
        .centred {
            text-align: center;
            display: block;
        }
        .tight-to-content {
            width: fit-content;
        }

        </style>

    """,
        unsafe_allow_html=True,
    )
with st.sidebar.container():
    with st.expander("how to read"):
        st.success("Highlights in Green")
        st.warning("Roadblocks in Yellow")
        st.expander("Asides in Accordions")

st.header("About Scrapeddit")
st.markdown(
    """##### An ETL suite for reddit scraping. Proving a range of tools to gather data in bulk. Supports scraping-"""
)
st.markdown(
    """
<div style="display:flex;flex-direction:row; gap:10px; flex-wrap:nowrap; justify-content:center; align-items:center; margin:12px 0;">
<span class="orange-button tight-to-content">Single Comments</span>
<span class="orange-button tight-to-content">Single Submissions  (Original posts of a thread)</span>
<span class="orange-button tight-to-content">Entire Threads</span>
<span class="orange-button tight-to-content">Entire Subreddits</span>
<span class="orange-button tight-to-content">Redditors comments</span>
<span class="orange-button tight-to-content">and more...</span>
</div>
""",
    unsafe_allow_html=True,
)

with st.expander("What is Reddit"):
    st.markdown(
        """[Reddit](https://www.reddit.com) is a social media site / forum hub where users can submit text,
         videos, photos and links which other users can comment and vote on.
    """
    )
    st.markdown(
        """
        Reddit is broken down into communities, subforums called *subreddits*, which are user created
        and moderated spaces for discussion on a particular topic. E.g. r/AWS, r/plants, r/movies etc.

         Because of Reddit's huge userbase (443.8 million weekly active users)
         It provides a wealth of data for analysis and there already exist 
         well developed API tools to assist with data extraction.
         """
    )
    st.markdown(
        """
    <span class="orange-button subheader centred">Types of Data</span> 
    """,
        unsafe_allow_html=True,
    )
    st.image("presentation/assets/orang.png")

    st.warning(
        """
    reddit allows for content and communities to be flagged as 18+, requiring verification/explicit approval
    to view. As the account this scraper was using to authenticate was not verified 18+ any comments,
    subreddits or redditors requested which were flagged 18+ returned no response.
    """
    )

with st.expander("Inception"):
    st.write(
        """To get reacquainted with APIs I decided to write a reddit
        REPL bot which would listen for mentions, take the comment
        mentioning it and evaluate the comment as code (*in a sandboxed
        environment*), then return the result as a reply"""
    )
    with st.container(horizontal=True):
        st.image("presentation/assets/bot1.png", width=300)
        st.image("presentation/assets/bot2.png", width=300)
    st.markdown(
        """
        After originally using the vanilla reddit API with the python response
        library, I discovered a more fully featured python library for the
        reddit API, **PRAW** which presents reddit data as objects.
        """
    )

with st.expander("Testing"):
    st.markdown(
        """
    ##### Testing done via pytest / pytest-cov, with-
    <div style="display:flex;flex-direction:column; gap:10px; flex-wrap:nowrap; justify-content:center; align-items:center; margin:12px 0;">
    <span class="orange-button ">55 Tests</span>
    <span class="orange-button ">Each ETL citical module having 100% coverage  (Original posts of a thread)</span>
    <span class="orange-button ">Over 70% total coverage</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

with st.container(border=True):
    st.page_link("pages/1_🔧Design.py", label="Design", width="stretch")
