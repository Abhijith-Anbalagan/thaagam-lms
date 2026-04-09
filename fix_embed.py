import sys

NEW_FN = """\
function getEmbedUrl(url) {
    // 1. Decode HTML entities
    url = url.replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#39;/g,"'");
    // 2. Extract src from a pasted <iframe> tag
    var iframeMatch = url.match(/src=["']([^"']+)["']/);
    if (iframeMatch) url = iframeMatch[1].replace(/&amp;/g,'&');
    // 3. Comprehensive YouTube regex - handles all formats
    var ytMatch = url.match(/(?:https?:\\/\\/)?(?:www\\.)?(?:youtube\\.com\\/(?:watch\\?(?:.*&)?v=|shorts\\/|embed\\/|v\\/)|youtu\\.be\\/)([A-Za-z0-9_-]{11})/);
    if (ytMatch) {
        return 'https://www.youtube-nocookie.com/embed/' + ytMatch[1]
             + '?autoplay=1&rel=0&origin=' + encodeURIComponent(window.location.origin);
    }
    // 4. Vimeo
    var vimeoMatch = url.match(/vimeo\\.com\\/(?:video\\/)?(\\d+)/);
    if (vimeoMatch) return 'https://player.vimeo.com/video/' + vimeoMatch[1] + '?autoplay=1';
    // 5. Unknown - caller shows fallback
    return null;
}
"""

for path in [
    'templates/superadmin/course_detail.html',
    'templates/student/course_detail.html',
]:
    with open(path, encoding='utf-8') as f:
        content = f.read()

    start = content.find('function getEmbedUrl(')
    if start == -1:
        sys.stdout.write('NOT FOUND in ' + path + '\n')
        continue

    end = content.find('\n}', start)
    if end == -1:
        sys.stdout.write('END NOT FOUND in ' + path + '\n')
        continue
    end += 2  # include the closing \n}

    new_content = content[:start] + NEW_FN + content[end:]
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    sys.stdout.write('Fixed: ' + path + '\n')
