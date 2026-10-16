# TOYz — Gallery sản phẩm (Tam Quốc)

Trang gallery sản phẩm dựng từ **bài đăng fanpage TOYz** (Pancake Page API): ảnh tải về máy
(không hotlink), nội dung lấy nguyên văn từ bài đăng.

## Tính năng
1. **Gallery** dạng lưới thẻ sản phẩm, có ô tìm kiếm (tên / SKU / giá / mô tả).
2. **Thumbnail tự chạy**: mỗi thẻ luân phiên chậm rãi giữa 2 ảnh đầu (crossfade 1,8s, đổi mỗi 4,5s, lệch pha giữa các thẻ).
3. **Popup chi tiết**: slide ảnh (mũi tên, dải thumbnail, số thứ tự) + thông tin sản phẩm (giá từng phiên bản, cọc, SKU, chất liệu, kích thước, ETA, hạn chốt đơn, giới hạn) + toàn văn bài đăng.
4. **Lightbox** khi bấm vào ảnh trong popup: zoom (+/−/lăn chuột/gấp đôi), kéo ảnh khi đã zoom, toàn màn hình, chuyển ảnh, dải thumbnail, số thứ tự, phím tắt (←/→, +/−, 0, F, Esc).

## Cấu trúc
```
index.html          trang chính
styles.css          giao diện (dark)
app.js              toàn bộ logic (vanilla JS, không thư viện ngoài)
data/products.json  dữ liệu sản phẩm (sinh tự động)
assets/<post_id>/   ảnh gốc (đã nén, max 1400px)
thumbs/<post_id>/   ảnh nhỏ cho gallery (max 520px)
build.py            sinh data + tải ảnh từ cache bài đăng
cdp_check.mjs       test tự động bằng Chrome DevTools Protocol
```

## Chạy thử tại máy
```bash
cd ~/toyz-gallery
python3 -m http.server 8765      # rồi mở http://127.0.0.1:8765
```

## Sinh lại dữ liệu
```bash
# 1) lấy bài đăng (cache ~/.hermes/state/toyz_posts_cache.json)
python3 ~/.hermes/scripts/toyz_page_posts_deep.py --months 12
# 2) lọc Tam Quốc + tải ảnh + sinh data/products.json
/Users/zc/.hermes/hermes-agent/venv/bin/python build.py --filter tamquoc --limit 40
```
Bộ lọc nằm ở `TAMQUOC` / `NOT_TAMQUOC` trong `build.py`; đổi `--filter all` để lấy mọi bài có ảnh.

## Test tự động
```bash
node cdp_check.mjs http://127.0.0.1:8765/index.html ./_shots
```
Kiểm tra: số thẻ, slideshow đổi ảnh, mở popup, chuyển ảnh, mở lightbox, zoom, Esc, lọc tìm kiếm,
và bắt lỗi console (kỳ vọng `consoleErrors: []`). Ảnh chụp lưu ở `_shots/`.

## Deploy GitHub Pages
Repo tĩnh, không cần build: push toàn bộ thư mục lên nhánh `main`, bật Pages → *Deploy from a branch* → `main` / `/ (root)`.
