# TOYz — Gallery sản phẩm (nhiều dòng, mỗi dòng 1 trang riêng)

Trang tĩnh dựng từ **bài đăng fanpage TOYz** (Pancake Page API): ảnh tải về máy (không hotlink),
nội dung lấy nguyên văn từ bài đăng. Một repo — một site Pages — **mỗi dòng sản phẩm một thư mục con**.

## Cấu trúc
```
index.html                     trang chọn dòng (sinh bởi make_landing.py)
styles.css  app.js             dùng chung cho mọi dòng (đường dẫn ../styles.css, ../app.js)
tam-quoc/                      dòng 1: 16 sản phẩm · 145 ảnh
  index.html  data/products.json  assets/<post_id>/  thumbs/<post_id>/
final-fantasy/                 dòng 2: 15 sản phẩm · 125 ảnh
  (cấu trúc y hệt)
build.py                       lọc post → tải ảnh → sinh data/products.json cho 1 dòng
make_landing.py                sinh trang chọn dòng ở gốc
prune_assets.py                xoá assets/thumbs không được products.json tham chiếu
verify_assets.py               kiểm tra mọi ảnh tham chiếu đều có trên đĩa
show_product.py <từ khoá> <dòng>   soi nhanh 1 sản phẩm trong data
cdp_check.mjs  cdp_mobile_check.mjs   test tự động bằng Chrome DevTools Protocol
```

## Tính năng mỗi trang dòng
1. **Gallery** lưới thẻ + ô tìm kiếm (tên / SKU / giá / mô tả, không phân biệt dấu).
2. **Thumbnail tự chạy**: luân phiên chậm rãi giữa 2 ảnh đầu (crossfade 1,8s, đổi mỗi 4,5s, lệch pha giữa các thẻ).
3. **Popup chi tiết**: slide ảnh (mũi tên, dải thumbnail, số thứ tự) + thông tin sản phẩm (giá từng phiên bản,
   cọc, SKU, chất liệu, kích thước, ETA, hạn chốt đơn, giới hạn) + toàn văn bài đăng + link bài gốc.
4. **Lightbox**: zoom (nút/lăn chuột/nhấp đôi), kéo ảnh khi đã zoom, toàn màn hình, chuyển ảnh,
   dải thumbnail, phím tắt (←/→, +/−, 0, F, Esc đóng lightbox trước rồi tới popup).

## Thêm 1 dòng mới (không cào lại)
```bash
cd ~/toyz-gallery
# 1) thêm mục vào LINES trong build.py:  "ten-dong": (regex nhận, regex loại)
# 2) dựng dòng mới (Pillow nằm ở venv Hermes)
/Users/zc/.hermes/hermes-agent/venv/bin/python build.py --filter ten-dong --max-img 10 \
  --out ~/toyz-gallery/ten-dong
# 3) copy index.html của dòng cũ, sửa <title>/tagline; rồi:
python3 prune_assets.py && python3 verify_assets.py && python3 make_landing.py
# 4) test + deploy
node cdp_check.mjs http://127.0.0.1:8765/ten-dong/ ./_shots
node cdp_mobile_check.mjs http://127.0.0.1:8765/ten-dong/ 390 844 ./_shots/mobile.png
git add -A && git commit -m "Thêm dòng ten-dong" && git push
```
Cache bài đăng: `~/.hermes/state/toyz_posts_cache.json` (2.323 post, 12 tháng) — muốn dữ liệu cũ hơn thì
chạy `python3 ~/.hermes/scripts/toyz_page_posts_deep.py --months 24` (cache tự nối thêm).

## Chạy thử tại máy
```bash
cd ~/toyz-gallery && python3 -m http.server 8765   # mở http://127.0.0.1:8765
```

## Ghi chú dữ liệu
- Giá shop ghi theo đơn vị **k** (`6.100k`) hoặc **tr** (`40 tr`); giá mơ hồ kiểu `6X tr` thì giữ nguyên chữ,
  không tự đoán số.
- Bài không tải được ảnh (attachment chỉ có link `photo.php` của Facebook) bị bỏ — script in rõ số bài bỏ.
- Tiêu đề lấy từ dòng tên sản phẩm trong bài; bài kiểu "thông báo/deal" thì tự tìm dòng có tên sản phẩm.

## Deploy
Repo tĩnh, không cần build: push nhánh `main`, Pages → *Deploy from a branch* → `main` / `/ (root)`.
Site: https://thntvn.github.io/toyz-gallery/ · sau mỗi lần push, build Pages ~2–3 phút.
