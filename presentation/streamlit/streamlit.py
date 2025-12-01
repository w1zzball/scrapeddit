import pandas as pd
import streamlit as st

st.title("Scrapeddit")

st.header("Scrapeddit")
st.write("A tool for bulk reddit scraping.")

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
        """To get reacquainted with APIs I decided to write a reddit bot which
         would listen for mentions, take the comment mentioning it and
        evaluate the comment as python code,
        then return the result as a reply"""
    )
