import os
import re
import struct
import sqlite3
import urllib.request
import json

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, 'db.sqlite3')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Read API key from .env
YT_API_KEY = ''
env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_path):
    for line in open(env_path):
        if line.startswith('YOUTUBE_API_KEY='):
            YT_API_KEY = line.strip().split('=', 1)[1]
            break


def get_yt_duration(video_id):
    if not YT_API_KEY or YT_API_KEY == 'YOUR_API_KEY_HERE':
        return 0
    try:
        url = ('https://www.googleapis.com/youtube/v3/videos'
               '?part=contentDetails&id=' + video_id + '&key=' + YT_API_KEY)
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        items = data.get('items', [])
        if not items:
            return 0
        iso = items[0]['contentDetails']['duration']
        h = int((re.search(r'(\d+)H', iso) or type('x',(),({}))()).group(1) if re.search(r'(\d+)H', iso) else 0)
        m = int(re.search(r'(\d+)M', iso).group(1)) if re.search(r'(\d+)M', iso) else 0
        s = int(re.search(r'(\d+)S', iso).group(1)) if re.search(r'(\d+)S', iso) else 0
        return h * 3600 + m * 60 + s
    except Exception as e:
        print('  YT API error: ' + str(e))
        return 0


def get_vimeo_duration(video_id):
    try:
        url = f'https://vimeo.com/api/oembed.json?url=https://vimeo.com/{video_id}'
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        return data.get('duration', 0)
    except Exception as e:
        print('  Vimeo API error: ' + str(e))
        return 0


def get_external_video_duration(video_url):
    # YouTube
    yt_match = re.search(r'youtube\.com/embed/([A-Za-z0-9_-]{11})', video_url or '')
    if yt_match:
        return get_yt_duration(yt_match.group(1))
    
    # Vimeo
    vimeo_match = re.search(r'player\.vimeo\.com/video/(\d+)', video_url or '')
    if vimeo_match:
        return get_vimeo_duration(vimeo_match.group(1))
    
    return 0


def get_duration(filepath):
    try:
        with open(filepath, 'rb') as f:
            data = f.read()

        def find_mvhd(data, offset, end):
            i = offset
            while i + 8 <= end:
                size = struct.unpack('>I', data[i:i+4])[0]
                if size < 8 or i + size > len(data):
                    break
                name = data[i+4:i+8]
                if name == b'mvhd':
                    version = data[i+8]
                    if version == 1:
                        ts = struct.unpack('>I', data[i+28:i+32])[0]
                        dn = struct.unpack('>Q', data[i+32:i+40])[0]
                    else:
                        ts = struct.unpack('>I', data[i+20:i+24])[0]
                        dn = struct.unpack('>I', data[i+24:i+28])[0]
                    if ts > 0:
                        return int(dn / ts)
                if name in (b'moov', b'trak', b'mdia', b'minf', b'stbl', b'udta'):
                    result = find_mvhd(data, i + 8, i + size)
                    if result:
                        return result
                i += size
            return 0

        return find_mvhd(data, 0, len(data))
    except Exception as e:
        print('  parse error: ' + str(e))
        return 0


def fmt(secs):
    if not secs:
        return '0m'
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    if h:
        return str(h) + 'h ' + str(m) + 'm ' + str(s) + 's'
    if m:
        return str(m) + 'm ' + str(s) + 's'
    return str(s) + 's'


conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

# ── 1. Backfill uploaded file videos ──
cur.execute("""
    SELECT id, title, file
    FROM superadmin_globalconceptvideo
    WHERE file != '' AND file IS NOT NULL AND duration_seconds = 0
""")
rows = cur.fetchall()
print('Found ' + str(len(rows)) + ' file videos with duration_seconds=0')

updated = 0
for vid_id, title, file_rel in rows:
    filepath = os.path.join(MEDIA_ROOT, file_rel)
    if not os.path.exists(filepath):
        print('  MISSING [' + str(vid_id) + '] ' + str(title))
        continue
    dur = get_duration(filepath)
    if dur > 0:
        cur.execute('UPDATE superadmin_globalconceptvideo SET duration_seconds=? WHERE id=?', (dur, vid_id))
        updated += 1
        print('  OK [' + str(vid_id) + '] ' + str(title or 'Untitled') + ' -> ' + fmt(dur))
    else:
        print('  FAIL [' + str(vid_id) + '] ' + str(title or 'Untitled') + ' -> could not read')

conn.commit()

# ── 2. Backfill external URL videos (YouTube, Vimeo, etc.) ──
cur.execute("""
    SELECT id, title, video_url
    FROM superadmin_globalconceptvideo
    WHERE video_url != '' AND video_url IS NOT NULL AND duration_seconds = 0
""")
external_rows = cur.fetchall()
print('Found ' + str(len(external_rows)) + ' external videos with duration_seconds=0')

external_updated = 0
for vid_id, title, video_url in external_rows:
    dur = get_external_video_duration(video_url)
    if dur > 0:
        cur.execute('UPDATE superadmin_globalconceptvideo SET duration_seconds=? WHERE id=?', (dur, vid_id))
        external_updated += 1
        
        # Determine platform for logging
        platform = 'Unknown'
        if 'youtube.com/embed/' in (video_url or ''):
            platform = 'YouTube'
        elif 'player.vimeo.com' in (video_url or ''):
            platform = 'Vimeo'
            
        print('  OK [' + str(vid_id) + '] ' + platform + ' - ' + str(title or 'Untitled') + ' -> ' + fmt(dur))
    else:
        # Determine why it failed
        if 'youtube.com/embed/' in (video_url or ''):
            print('  FAIL [' + str(vid_id) + '] YouTube - ' + str(title or 'Untitled') + ' -> API key missing or error')
        elif 'player.vimeo.com' in (video_url or ''):
            print('  FAIL [' + str(vid_id) + '] Vimeo - ' + str(title or 'Untitled') + ' -> API error')
        else:
            print('  SKIP [' + str(vid_id) + '] Unsupported platform: ' + str(video_url))

conn.commit()

cur.execute('SELECT id FROM superadmin_globalcourse')
course_ids = [r[0] for r in cur.fetchall()]
courses_updated = 0
for cid in course_ids:
    cur.execute("""
        SELECT COALESCE(SUM(v.duration_seconds), 0)
        FROM superadmin_globalconceptvideo v
        JOIN superadmin_globalconcept c ON v.concept_id = c.id
        WHERE c.course_id = ?
    """, (cid,))
    total_secs = cur.fetchone()[0]
    total_hours = round(total_secs / 3600, 1)
    cur.execute('UPDATE superadmin_globalcourse SET total_hours=? WHERE id=?', (total_hours, cid))
    if total_secs > 0:
        courses_updated += 1
        print('  Course [' + str(cid) + '] -> ' + fmt(total_secs) + ' (' + str(total_hours) + 'h)')

conn.commit()
conn.close()

print('Done. Updated ' + str(updated) + '/' + str(len(rows)) + ' file videos, ' + str(external_updated) + '/' + str(len(external_rows)) + ' external videos. Synced ' + str(courses_updated) + ' courses.')
