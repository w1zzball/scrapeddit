from .connection_utils import with_resources


@with_resources
def get_submission(reddit, conn, post_id):
    # cur = conn.cursor()
    submission = reddit.submission(id=post_id)
    return submission
