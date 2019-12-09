# Notes
- In index.html, we could link to the person's about me page instead of the base url
- There are a lot of places where I think we could extract logic into re-usable modules (or packages), but given the time
and knowledge I have, left it as is(...first and foremost, it needs to work)
- I've left notes in various files if there are things I thought of that would be quick, good improvements, but either
ran out of time or didn't know how to do them

#### Archive Page
- For the archive page, we would pass a filtered list of posts to a view using: 
`db.session.query(Post).filter(Post.pub_date >= (archive_month/archive_year) and Post.pub_date <= (archive_month + 1/archive_year)).order_by(Post.pub_date)`
- To get the correct month/year pairing, we'd probably need to do some conversion of the month/year, unsure, although
in Javascript land, we could use something like moment to compare the dates or even the native Date object
- We could then define a new method `get_archive_posts(archive_month, archive_year)` and use that to retrieve the posts
- Then we would pass the results into the view just the same as in index.html