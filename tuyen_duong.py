"""Chay mot lan (26/10/2026): chen muc "Tuyen van chuyen va cang quan trong" vao trang Nong san (299)
va Nguyen lieu cong nghiep (301). Noi dung tinh (dia ly it thay doi), chi chen khi chua co.
"""
import wp

NS = [
    ["Sông Mississippi và cảng vịnh Mexico (New Orleans, Baton Rouge)", "Ngô, đậu tương, lúa mì Mỹ",
     "Cửa ngõ xuất khẩu ngũ cốc lớn nhất của Mỹ. Mực nước sông thấp vào mùa thu làm sà lan phải chở nhẹ, cước tăng, giá tại cảng (basis) biến động."],
    ["Cảng Tây Bắc Thái Bình Dương (Seattle, Tacoma, Portland, Kalama)", "Ngô, đậu tương, lúa mì Mỹ",
     "Đường ngắn nhất từ Mỹ sang Trung Quốc, Nhật Bản, Hàn Quốc."],
    ["Santos, Paranaguá (Brazil)", "Đậu tương, ngô, khô đậu",
     "Hai cảng nông sản lớn nhất Brazil; hàng đợi tàu kéo dài vào cao điểm thu hoạch đậu tương (tháng 2 – 5)."],
    ["Cảng vòng cung phía Bắc Brazil (Itaqui, Barcarena, Santarém)", "Đậu tương, ngô",
     "Tỷ trọng tăng nhanh nhờ gần vùng trồng Mato Grosso, rút ngắn đường sang châu Á."],
    ["Cụm cảng Rosario trên sông Paraná (Argentina)", "Khô đậu, dầu đậu, ngô, lúa mì",
     "Trung tâm xuất khẩu khô đậu và dầu đậu lớn nhất thế giới; khi sông Paraná cạn, tàu phải chở ít hàng hơn."],
    ["Biển Đen (Novorossiysk, Odesa, Chornomorsk, Constanța)", "Lúa mì, ngô, dầu hướng dương",
     "Nguồn lúa mì lớn nhất thế giới (Nga, Ukraine); chịu rủi ro xung đột; hàng ra Địa Trung Hải phải qua eo Bosporus."],
    ["Kênh đào Panama", "Ngô, đậu tương từ vịnh Mexico sang châu Á",
     "Bị hạn chế số lượt tàu khi hạn hán làm cạn hồ Gatun (như năm 2023–2024, thường liên quan El Niño)."],
    ["Kênh Suez và eo Bab el-Mandeb (Biển Đỏ)", "Lúa mì Biển Đen, châu Âu sang châu Á, Đông Phi",
     "Khi Biển Đỏ mất an toàn, tàu vòng qua mũi Hảo Vọng, thêm 10–14 ngày và tăng cước."],
    ["Eo biển Malacca", "Ngũ cốc nhập vào Đông Á, dầu cọ xuất khẩu",
     "Tuyến hàng hải bận rộn nhất châu Á, nối Ấn Độ Dương với Biển Đông."],
    ["Cảng Thái Lan (Bangkok, Laem Chabang), Ấn Độ (Kakinada), TP.HCM", "Gạo",
     "Ba nước xuất khẩu gạo lớn nhất (Ấn Độ, Thái Lan, Việt Nam); chính sách xuất khẩu của Ấn Độ tác động mạnh tới giá."],
    ["Cảng Việt Nam (Cái Mép – Thị Vải, Cát Lái, Hải Phòng)", "Nhập ngô, đậu tương, khô đậu, lúa mì",
     "Việt Nam nhập khẩu lớn nguyên liệu thức ăn chăn nuôi, chủ yếu từ Brazil, Argentina, Mỹ."],
]
NLCN = [
    ["Santos (Brazil)", "Cà phê arabica, đường thô, bông",
     "Cảng xuất khẩu cà phê và đường lớn nhất thế giới; tắc nghẽn ở Santos thường kéo giá arabica và đường tăng."],
    ["Vitória (Brazil)", "Cà phê conilon (robusta Brazil)", "Cửa ngõ của bang Espírito Santo, vùng trồng conilon chính."],
    ["Cát Lái, Cái Mép – Thị Vải (TP.HCM, Bà Rịa – Vũng Tàu)", "Cà phê robusta, cao su, hạt điều",
     "Phần lớn cà phê Việt Nam (nước xuất khẩu robusta lớn nhất) đi qua cụm cảng này."],
    ["Panjang (Lampung, Indonesia)", "Cà phê robusta", "Cảng xuất robusta chính của Indonesia."],
    ["Buenaventura, Cartagena (Colombia)", "Cà phê arabica", "Cửa ngõ cà phê Colombia ra Thái Bình Dương và Đại Tây Dương."],
    ["Abidjan, San Pédro (Bờ Biển Ngà); Tema, Takoradi (Ghana)", "Ca cao",
     "Hai nước này cung cấp khoảng 60% ca cao thế giới; thời tiết Tây Phi và tiến độ hàng về cảng quyết định giá ca cao."],
    ["Laem Chabang, Songkhla (Thái Lan); Belawan (Indonesia); Port Klang (Malaysia)", "Cao su thiên nhiên",
     "Thái Lan, Indonesia, Việt Nam là ba nước xuất khẩu cao su lớn nhất, điểm đến chính là Trung Quốc."],
    ["Houston và cảng vùng Vịnh, Savannah (Mỹ); Santos (Brazil)", "Bông",
     "Mỹ và Brazil là hai nước xuất khẩu bông lớn nhất; khách hàng chính là Việt Nam, Bangladesh (Chittagong), Trung Quốc, Pakistan."],
    ["Kandla, Mumbai (Ấn Độ); Laem Chabang (Thái Lan)", "Đường",
     "Ấn Độ, Thái Lan là hai nguồn đường lớn sau Brazil; hạn ngạch xuất khẩu của Ấn Độ tác động mạnh tới giá."],
    ["Kho đạt chuẩn sàn ICE (Antwerp, Hamburg, Bremen, Trieste, Barcelona, New Orleans, Houston, New York)", "Cà phê arabica, ca cao",
     "Tồn kho chứng nhận tại các kho này là chỉ báo cung ngắn hạn theo dõi hằng ngày."],
    ["Kênh Suez, Biển Đỏ, eo Malacca", "Cà phê, cao su châu Á sang châu Âu",
     "Khi Biển Đỏ mất an toàn, tàu vòng qua châu Phi làm chậm hàng về châu Âu, tồn kho ICE châu Âu giảm."],
]


def khoi(ma, ten, rows):
    tr = "".join('<tr><td><b>%s</b></td><td>%s</td><td>%s</td></tr>' % tuple(r) for r in rows)
    return ('<!-- wp:heading -->\n<h2 class="wp-block-heading" id="tuyen-van-chuyen">Tuyến vận chuyển và cảng quan trọng: %s</h2>\n<!-- /wp:heading -->\n\n'
            '<!-- wp:html -->\n<div class="gdtd" id="gdtd-%s"><style>.gdtd{overflow-x:auto;margin:8px 0 24px}'
            '.gdtd table{border-collapse:collapse;width:100%%;font-size:14px;min-width:620px}'
            '.gdtd th,.gdtd td{padding:8px;border-bottom:1px solid #eee;text-align:left;vertical-align:top;line-height:1.5}'
            '.gdtd th{background:#faf7f7;font-weight:600;color:#444}.gdtd td:first-child{width:30%%}.gdtd td:nth-child(2){width:22%%}'
            '.gdtd p{font-size:13px;color:#666;margin:8px 0 0}</style>'
            '<table><tr><th>Tuyến, cảng</th><th>Hàng hóa chính</th><th>Vai trò và rủi ro</th></tr>%s</table>'
            '<p>Gián đoạn tại các điểm này (thời tiết, mực nước sông, xung đột, đình công) thường làm tăng cước vận tải, kéo dài thời gian giao hàng và đẩy giá kỳ hạn tăng. Nội dung tham khảo.</p>'
            '</div>\n<!-- /wp:html -->\n' % (ten, ma, tr))


def run():
    if not wp.enabled():
        raise RuntimeError("Thieu WP_URL/WP_USER/WP_APP_PASSWORD")
    out = []
    for pid, ma, ten, rows in ((299, "ns", "nông sản", NS), (301, "nlcn", "nguyên liệu công nghiệp", NLCN)):
        raw = wp.get_raw(pid)
        if 'id="gdtd-%s"' % ma in raw:
            out.append("%d da co" % pid)
            continue
        wp.backup_raw(pid, raw)
        wp.set_raw(pid, raw.rstrip() + "\n\n" + khoi(ma, ten, rows))
        out.append("%d da chen" % pid)
    return "; ".join(out)
