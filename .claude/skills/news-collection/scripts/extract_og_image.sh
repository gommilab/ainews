#!/usr/bin/env bash
# 한 URL에서 대표 이미지 URL을 추출한다.
# 우선순위: og:image -> twitter:image -> 본문 첫 <img src>.
# 사용: extract_og_image.sh "https://example.com/article"
# 출력: 찾은 이미지 URL 한 줄(없으면 빈 출력, 종료코드 1).
set -euo pipefail
url="${1:-}"
[ -z "$url" ] && { echo "usage: extract_og_image.sh <url>" >&2; exit 2; }

html="$(curl -fsSL -A 'Mozilla/5.0 (compatible; ainews-brief/1.0)' --max-time 25 "$url" 2>/dev/null || true)"
[ -z "$html" ] && exit 1

# meta og:image / twitter:image (property 또는 name, 속성 순서 무관)
pick_meta() {
  local key="$1"
  printf '%s' "$html" \
    | grep -ioE "<meta[^>]+(property|name)=[\"']${key}[\"'][^>]*>" \
    | grep -ioE "content=[\"'][^\"']+[\"']" \
    | head -n1 \
    | sed -E "s/content=[\"']([^\"']+)[\"']/\1/I"
}

img="$(pick_meta 'og:image')"
[ -z "$img" ] && img="$(pick_meta 'twitter:image')"

# 폴백: 본문 첫 <img src>
if [ -z "$img" ]; then
  img="$(printf '%s' "$html" | grep -ioE '<img[^>]+src=[\"'\''][^\"'\'']+[\"'\'']' | head -n1 | sed -E 's/.*src=[\"'\'']([^\"'\'']+)[\"'\''].*/\1/I')"
fi

[ -z "$img" ] && exit 1

# 상대경로 보정(//, /path)
case "$img" in
  //*) img="https:$img" ;;
  /*)  base="$(printf '%s' "$url" | sed -E 's#(https?://[^/]+).*#\1#')"; img="$base$img" ;;
esac

printf '%s\n' "$img"
