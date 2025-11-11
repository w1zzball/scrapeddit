from .connection_utils import with_resources


@with_resources(use_reddit=True, use_db=False)
def get_submission(reddit, post_id=None, post_url=None):
    if post_id:
        submission = reddit.submission(id=post_id)
    elif post_url:
        submission = reddit.submission(url=post_url)
    else:
        raise ValueError("Either post_id or post_url must be provided.")
    return submission
