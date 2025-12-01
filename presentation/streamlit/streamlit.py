import pandas as pd
import streamlit as st

st.title("Scrapeddit")

st.sidebar.success("select a page")

st.header("Scrapeddit")
st.write("An ETL suite for reddit scraping.")

with st.expander("What is reddit"):
    st.write(
        """Reddit is a social media site / forum where users can submit text,
         videos, photos and links which other users can comment and vote on"""
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
    st.markdown(
        """
        After originally using the vanilla reddit API with the python response
        library, I discovered a more fully featured python library for the
        reddit API, **PRAW** which presents reddit data as objects.
        """
    )
