netflixXBMC
===========

A netflix crawler. Collects TV shows and Movies. Creates directory hierarchy then saves a NFO and empty .avi file to disk

What's provided by the user?
- login email
- login password
- path to save collected information
* none of this information is made public

This crawler signs into nexflix with the login and password you provide. Then, it finds the "Browse" navigation widget and traverses through the genres and subgenres create a directory for each. If a movie is found a directory is created with the title of the movie. If a show is found with a collection such as seasons & series a directory is with the title of the show and a subdirectory with the collection's name (Season 1 or Series 1).

At each directory's end point is a NFO and an empty .avi file. 
The NFO and .avi is formatted to be reconized by XBMC.
The .avi and NFO will have the same base same.

--
The .avi: Episode 1_s01_e01.avi

The NFO: Episode 1_s01_e01.nfo
```xml
<episodedetails>
    <title>Episode 1</title>
    <season>1</season>
    <episode>1</episode>
    <plot>Using his journal to prompt his memory, the doctor recalls his youth, when he was sent to the frigid tundra of rural Russia at age 25.</plot>
    <playURL>http://www.netflix.com/WiPlayer?movieid=70277577&trkid=13467549</playURL>
    <thumb>http://so1.akam.nflximg.com/soa4/155/1026209155.jpg</thumb>
</episodedetails>
```

The intention!

This is intended to be the backend for a XBMC netflix plugin. A UI still needs to be created for this. By someone who enjoys creating XBMC interfaces. 

This collect shows and movies from netflix and save reference files to disk. XBMC indexes the files saved by the crawler. When a XBMC user selects a .avi file to play the corrisponding NFO is then read and passes the playURL tag.text to a web browser or somehow plays inside XBMC. 

