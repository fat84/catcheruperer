
import db

import json
import random
import os

import spotipy
import spotipy.util as util

from dateutil import parser
from datetime import timedelta

ONE_WEEK = timedelta(weeks=1)

def load_spdata():
    d = json.load(open("spotify-data.json"))
    new_d = {}
    for meta, data in d:
        new_d["%s - %s" % (meta[0], meta[1])] = data
    return new_d

spdata = load_spdata()

def make_playlist(artist, title, hours):

    stats = db.stats(artist, title)
    start = stats['first']

    print stats

    # At first we make a basic assumption that a song is 4 minutes long
    songs_per_hour = 60.0/4

    number_years = 2015 - int(start[:4])

    if number_years > hours:
        actual_hours = number_years
    else:
        actual_hours = hours

    available_slots = actual_hours * songs_per_hour

    print "actual hours %s avail slots %s" % (actual_hours, available_slots)

    # first start with the first year -> end of that year
    allsongs = songs_for_year(start)
    # then go one per year until the last year
    allsongs = []
    lastyear = 2015
    year = int(start[:4])
    while year <= lastyear:
        print "songs for", year
        allsongs.extend(songs_for_year("%s-01-01" % year))
        year += 1

    # We now have too many songs. See how many we need to throw away
    remove_prob = float(available_slots)/len(allsongs)
    print "removing with prob of", remove_prob

    songs = []
    lastsong = None
    for s in allsongs:
        if random.random() < remove_prob and s != lastsong:
            songs.append(s)
            lastsong = s

    return actual_hours, songs

def weighted_choice(choices):
    total = sum(w for c, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices:
        if upto + w >= r:
            return c
        upto += w
    assert False, "Shouldn't get here"

def songs_for_year(fromdate):
    # From the from date (which could be in the middle of the year)
    # until -12-31 of that year, give 1 random song per week
    finaldate = "%s-12-31" % fromdate[:4]

    yearsongs = []

    # todate = fromdate + 1 week
    fromparse = parser.parse(fromdate)
    toparse = fromparse + ONE_WEEK
    todate = toparse.isoformat()[:10]
    while todate < finaldate:
        # TODO: Optimise to not do 1 `between` call per week
        songs = db.between(fromdate, todate)
        # TODO XXX Important - this doesn't do area under curve if
        #      it has from and to date - it has to have the artist and track instead

        sumweights = float(sum([s[0] for s in songs]))
        tochoose = []
        for s in songs:
            tochoose.append( ("%s - %s" % (s[1], s[2]), s[0]/sumweights) )
            # TODO: Don't need to divide by sum, weighted_choice does it
            # TODO: Weight by inverse-log of position on chart
            # TODO: Return metadata separate, plus week it was on the chart

        song = weighted_choice(tochoose)
        yearsongs.append(song)

        # add one week to todate
        toparse = toparse + ONE_WEEK
        todate = toparse.isoformat()[:10]

    return yearsongs

def songs_to_spotifyid(songs):
    ret = []
    for s in songs:
        if s in spdata:
            ret.append(spdata[s]["uri"])
    return ret

def create_spotify_playlist(playlist_name, track_ids):
    username = 'alastairporter'
    scope = 'playlist-modify-public'
    token = util.prompt_for_user_token(username, scope)
    sp = spotipy.Spotify(auth=token)

    playlist = sp.user_playlist_create(username, playlist_name)
    playlist_id = playlist["id"]

    c = 0
    while c < len(track_ids):
        toadd = track_ids[c:c+100]
        sp.user_playlist_add_tracks(username, playlist_id, toadd)
        c += 100


    url = playlist["external_urls"]["spotify"]
    code = playlist["uri"]

    return playlist_id, url, code

def cache_playlist(meta, tracks):
    try:
        os.makedirs("playlists")
    except:
        pass

    title = meta["title"]

    filename = os.path.join("playlists", "%s.json" % playlistid)

    items = {
                "startDate":"1962,12,10",
                "endDate":"1962,12,11",
                "headline":"Tic Toc",
                "text":"<p>Lords Of The Underground</p>",
                "asset": {
                    "media":"https://i.scdn.co/image/8f287f3a098826e5f8d3a9c2351ad5de0fd84901",
                    "thumbnail":"https://i.scdn.co/image/8f287f3a098826e5f8d3a9c2351ad5de0fd84901",
                    "credit":"",
                    "caption":""
                }
            }

    data = {"timeline":
    {
        "headline": title,
        "type":"default",
        "text":"",
        "asset": {
            "media":"https://i.scdn.co/image/8f287f3a098826e5f8d3a9c2351ad5de0fd84901",
            "thumbnail":"https://i.scdn.co/image/8f287f3a098826e5f8d3a9c2351ad5de0fd84901",
            "credit":"",
            "caption":""
        },
        "date": []
        }}

    res = {"meta": meta, "data": data}
    json.dump(res, open(filename, "w"))
