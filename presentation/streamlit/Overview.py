import streamlit as st

st.markdown(
    '<h1 style="color:#FF4500"><b>Scrapeddit</b></h1>', unsafe_allow_html=True
)

with st.sidebar.container():
    with st.expander("how to read"):
        st.success("Highlights in Green")
        st.warning("Roadblocks in Yellow")
        st.expander("Asides in Accordions")

st.header("About Scrapeddit")
st.markdown(
    """An ETL suite for reddit scraping. Proving a range of tools to
gather data in bulk. Supports scraping-
- Single Comments
- Single Submissions (Original posts of a thread)
- Entire Threads
- Entire Subreddits
- Redditors comment history
- and more...
"""
)

with st.expander("What is Reddit"):
    st.markdown(
        """[Reddit](https://www.reddit.com) is a social media site / forum where users can submit text,
         videos, photos and links which other users can comment and vote on.
         Because of Reddits huge userbase (443.8 million weekly active users)
         It provides a wealth of data for analysis and there already exist 
         well developed API tools to assist with data extraction.
         """
    )
    st.markdown("### Types of data available")
    st.markdown(
        """
            - text : body of a comment
            - image data : image included with submission
            - votes : sum of up/downvotes
            - date : date of creation / edit
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
