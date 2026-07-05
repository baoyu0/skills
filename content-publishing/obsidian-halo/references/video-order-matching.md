# Video Order Matching via Perceptual Hash

When user downloads X Article videos from 猫抓 (cat-catch), the downloaded files are numbered by Chrome's download order, which **does NOT match the article's DOM order**. This technique uses perceptual image hashing to match each video to its correct position.

## How It Works

Each X Article `<video>` has a `poster` attribute pointing to an amplify_video_thumb image on `pbs.twimg.com`. By comparing these poster images to the first frame of each downloaded video, we can determine which video belongs where.

## Steps

### 1. Download Poster Images from X Article

```bash
for url in "https://pbs.twimg.com/amplify_video_thumb/ID1/img/NAME.jpg" \
           "https://pbs.twimg.com/amplify_video_thumb/ID2/img/NAME.jpg" ...; do
  curl -sL -o poster-$i.jpg "$url"
done
```

### 2. Extract Video First Frames

```bash
for i in 1 2 3 4 5; do
  ffmpeg -y -i fpv-video-$i.mp4 -vframes 1 -q:v 2 thumb-$i.jpg
done
```

### 3. Compute Perceptual Hashes and Match

Use Python PIL `average_hash` (16x16) and hamming distance:

```python
from PIL import Image

def average_hash(path):
    img = Image.open(path).convert('L').resize((16, 16))
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    return ''.join('1' if p > avg else '0' for p in pixels)

def hamming(h1, h2):
    return sum(a != b for a, b in zip(h1, h2))

for pi in range(num_posters):
    scores = [(vi, hamming(poster_hash[pi], thumb_hash[vi])) for vi in range(num_videos)]
    best = min(scores, key=lambda x: x[1])
    print(f'poster #{pi+1} -> video #{best[0]+1} (hamming={best[1]})')
```

**Interpretation:**
- hamming=0 -> identical (perfect match)
- hamming=1~5 -> same video (excellent match)
- hamming>50 -> different video

### 4. Apply Mapping

Swap the `<video>` source URLs in the markdown file to match the correct order.

## Edge Cases

- **First frame is black/fade-in**: Try `-ss 0.5` or `-ss 2` offset rather than the very first frame
- **Mismatched dimensions**: 1280x720 vs 1470x630 doesn't affect the hash but can be a secondary signal
- **PIL path issues**: If `from PIL import Image` fails, use miniconda's Python:
  ```python
  import sys
  sys.path = [p for p in sys.path if 'hermes' not in p]
  from PIL import Image
  ```

## Why This Is Needed

cat-catch downloads videos in **detection order** (the order the browser requested the CDN URLs), not the order they appear in the article. The first video the user clicked play on gets download number 1, regardless of position. Perceptual hash matching is the reliable way to re-sync them.
