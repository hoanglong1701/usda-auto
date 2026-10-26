"""Bao cao COT (Commitments of Traders, CFTC), ban Disaggregated Futures Only, hang tuan.

Nguon: tep lich su theo nam cua CFTC (cftc.gov/files/dea/history/fut_disagg_txt_<nam>.zip) + tep tuan moi nhat.
Ghi vao trang du lieu an "du-lieu-cot" (tu tao neu chua co), 104 tuan gan nhat cho moi hop dong.
Lan dau (va khi thieu) chen khoi bieu do COT vao trang hien thi cua tung nhom.
CFTC cong bo chieu thu Sau (gio My), so lieu chot ngay thu Ba cung tuan.
"""
import io
import csv
import zipfile
import datetime
import requests
import wp

SLUG = "du-lieu-cot"
UA = {"User-Agent": wp.UA}
TUAN = 104
# ma CFTC, khoa, ten, nhom
SP = [
    ("002602", "ngo", "Ngô (CBOT)", "ns"), ("005602", "dau_tuong", "Đậu tương (CBOT)", "ns"),
    ("001602", "lua_mi", "Lúa mì SRW (CBOT)", "ns"), ("001612", "lua_mi_hrw", "Lúa mì HRW (KC)", "ns"),
    ("026603", "kho_dau", "Khô đậu tương (CBOT)", "ns"), ("007601", "dau_dau", "Dầu đậu tương (CBOT)", "ns"),
    ("039601", "gao", "Gạo thô (CBOT)", "ns"),
    ("083731", "arabica", "Cà phê arabica (ICE US)", "nlcn"), ("080732", "duong", "Đường 11 (ICE US)", "nlcn"),
    ("033661", "bong", "Bông (ICE US)", "nlcn"), ("073732", "ca_cao", "Ca cao (ICE US)", "nlcn"),
    ("085692", "dong", "Đồng (COMEX)", "kl"), ("076651", "bach_kim", "Bạch kim (NYMEX)", "kl"),
    ("075651", "paladi", "Palađi (NYMEX)", "kl"),
    ("088691", "vang", "Vàng (COMEX)", "vb"), ("084691", "bac", "Bạc (COMEX)", "vb"),
    ("067651", "wti", "Dầu thô WTI (NYMEX)", "nl"), ("023651", "khi", "Khí tự nhiên Henry Hub (NYMEX)", "nl"),
]
# cot trong tep CFTC (khong tieu de): 2 ngay, 3 ma HD, 7 OI, 8-9 nha SX long/short, 10-11 swap long/short,
# 13-14 quy dau co long/short, 16-17 to chuc khac long/short, 21-22 nho le long/short
COL = {"oi": 7, "pml": 8, "pms": 9, "swl": 10, "sws": 11, "mml": 13, "mms": 14, "orl": 16, "ors": 17, "nrl": 21, "nrs": 22}
# trang hien thi cua tung nhom
TRANG = {"ns": 299, "kl": 300, "nlcn": 301, "vb": 111, "nl": 302}
TEN_NHOM = {"ns": "nông sản", "kl": "kim loại", "nlcn": "nguyên liệu công nghiệp", "vb": "vàng, bạc", "nl": "năng lượng"}


def _rows(text):
    for r in csv.reader(io.StringIO(text)):
        if len(r) > 22 and r[3].strip()[:1].isdigit():
            yield r


def tai():
    """{ma: {ngay: {truong: so}}}"""
    ma = {c for c, *_ in SP}
    out = {}
    nam = datetime.date.today().year
    nguon = []
    for y in (nam - 2, nam - 1, nam):
        try:
            r = requests.get("https://www.cftc.gov/files/dea/history/fut_disagg_txt_%d.zip" % y, headers=UA, timeout=180)
            r.raise_for_status()
            z = zipfile.ZipFile(io.BytesIO(r.content))
            nguon.append(z.read(z.namelist()[0]).decode("latin-1"))
        except Exception:  # noqa  nam hien tai co the chua co tep dau nam
            if y != nam:
                raise
    r = requests.get("https://www.cftc.gov/dea/newcot/f_disagg.txt", headers=UA, timeout=120)
    r.raise_for_status()
    nguon.append(r.content.decode("latin-1"))
    for text in nguon:
        for r in _rows(text):
            c = r[3].strip()
            if c not in ma:
                continue
            d = r[2].strip()[:10]
            try:
                out.setdefault(c, {})[d] = {k: int(float(r[i].strip() or 0)) for k, i in COL.items()}
            except ValueError:
                continue
    return out


def dung(raw):
    obj = {"asof": "", "sp": [], "d": {}}
    for c, k, ten, nhom in SP:
        s = raw.get(c)
        if not s:
            continue
        ds = sorted(s)[-TUAN:]
        g = lambda f: [s[d][f] for d in ds]  # noqa
        obj["sp"].append([k, ten, nhom])
        obj["d"][k] = {"d": ds, "oi": g("oi"), "mml": g("mml"), "mms": g("mms"), "pml": g("pml"), "pms": g("pms"),
                       "swl": g("swl"), "sws": g("sws"), "orl": g("orl"), "ors": g("ors"), "nrl": g("nrl"), "nrs": g("nrs")}
        obj["asof"] = max(obj["asof"], ds[-1])
    if len(obj["sp"]) < len(SP) - 3:
        raise RuntimeError("COT thieu nhieu hop dong (%d/%d)" % (len(obj["sp"]), len(SP)))
    return obj


def tim_trang(s):
    base = wp._cfg()[0] + "/index.php/wp-json/wp/v2/pages"
    r = s.get(base, params={"slug": SLUG, "status": "publish,draft", "context": "edit", "_fields": "id"}, timeout=60)
    r.raise_for_status()
    if r.json():
        return r.json()[0]["id"], False
    c = s.post(base, json={"title": "Dữ liệu COT", "slug": SLUG, "status": "publish",
                           "content": '<!-- wp:html -->\n<pre id="gd-data" style="display:none">{}</pre>\n<!-- /wp:html -->'}, timeout=60)
    if c.status_code >= 400:
        raise RuntimeError("Tao trang du lieu COT loi %d: %s" % (c.status_code, c.text[:200]))
    return c.json()["id"], True


def khoi(nhom):
    """Khoi HTML+JS hien thi COT cho mot nhom (khong dung ky tu va)."""
    return KHOI.replace("__NHOM__", nhom).replace("__TEN__", TEN_NHOM[nhom])


def chen_khoi(notes):
    for nhom, pid in TRANG.items():
        raw = wp.get_raw(pid)
        if 'id="gdcot-%s"' % nhom in raw:
            continue
        wp.backup_raw(pid, raw)
        wp.set_raw(pid, raw.rstrip() + "\n\n" + khoi(nhom))
        notes.append("chen khoi COT trang %d" % pid)


def run(dry=False):
    if not wp.enabled():
        raise RuntimeError("Thieu WP_URL/WP_USER/WP_APP_PASSWORD")
    obj = dung(tai())
    notes = ["COT tuan %s, %d hop dong" % (obj["asof"], len(obj["sp"]))]
    if dry:
        return "(thu) " + notes[0]
    pid, moi = tim_trang(wp._sess())
    if not moi:
        try:
            old = wp.load(pid)
            if old.get("asof") == obj["asof"] and len(old.get("sp", [])) == len(obj["sp"]):
                notes.append("khong doi")
                chen_khoi(notes)
                return "; ".join(notes)
        except RuntimeError:
            pass
    wp.save(pid, obj)
    notes.append("ghi trang %d%s" % (pid, " (moi tao)" if moi else ""))
    chen_khoi(notes)
    return "; ".join(notes)


def run_dry():
    return run(dry=True)


KHOI = r'''<!-- wp:heading -->
<h2 class="wp-block-heading" id="cot-__NHOM__">Vị thế COT (CFTC): __TEN__</h2>
<!-- /wp:heading -->

<!-- wp:html -->
<style>
.gdcot{font-family:inherit;color:#222;margin:8px 0 24px}
.gdcot .c-sub{font-size:13px;color:#666;margin:0 0 10px;line-height:1.5}
.gdcot .c-box{border:1px solid #e6dede;border-radius:10px;padding:14px;background:#fff}
.gdcot .c-row{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 10px}
.gdcot .c-row button{border:1px solid #d9d2d2;background:#fff;color:#222;border-radius:999px;padding:6px 13px;font-size:14px;cursor:pointer;font-family:inherit}
.gdcot .c-row button.on{background:#c00000;border-color:#c00000;color:#fff;font-weight:600}
.gdcot .c-sum{font-size:14px;line-height:1.6;margin:6px 0 10px}
.gdcot svg{width:100%;height:auto;display:block}
.gdcot .c-lg{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px;margin:6px 0}
.gdcot .c-lg b{width:11px;height:11px;border-radius:3px;display:inline-block;margin-right:5px;vertical-align:-1px}
.gdcot .c-tw{overflow-x:auto}
.gdcot table{border-collapse:collapse;width:100%;font-size:14px;min-width:560px}
.gdcot th,.gdcot td{padding:6px 8px;border-bottom:1px solid #eee;text-align:right;white-space:nowrap}
.gdcot th:first-child,.gdcot td:first-child{text-align:left}
.gdcot th{background:#faf7f7;font-weight:600;color:#444}
.gdcot .up{color:#0a7a3d}.gdcot .dn{color:#c00000}
.gdcot .c-note{font-size:13px;color:#666;margin:8px 0 0;line-height:1.55}
</style>
<div class="gdcot" id="gdcot-__NHOM__">
<p class="c-sub">Báo cáo Commitments of Traders của Ủy ban Giao dịch Hàng hóa Tương lai Mỹ (CFTC), số liệu chốt thứ Ba, công bố tối thứ Sáu (sáng thứ Bảy giờ Việt Nam). Vị thế ròng = mua trừ bán, đơn vị hợp đồng.</p>
<div class="c-box">
<div class="c-row" data-r="btn"></div>
<p class="c-sum" data-r="sum">Đang tải số liệu…</p>
<div data-r="ch"></div>
<div class="c-lg"><span><b style="background:#2f6db3"></b>Quỹ đầu cơ (Managed Money) ròng</span><span><b style="background:#8a8080"></b>Nhà sản xuất, thương mại ròng</span><span><b style="background:#e0a100"></b>Swap dealer ròng</span></div>
<div class="c-tw" data-r="tb"></div>
<p class="c-note">Quỹ đầu cơ (Managed Money): quỹ đầu tư, CTA, thường theo xu hướng giá. Nhà sản xuất, thương mại: doanh nghiệp sản xuất, chế biến, kinh doanh hàng thật, thường bán để phòng hộ. Vị thế ròng của quỹ đầu cơ ở mức cực trị (rất cao hoặc rất thấp so với 2 năm) thường đi kèm rủi ro đảo chiều. Nội dung tham khảo, không phải khuyến nghị đầu tư.</p>
</div>
</div>
<script>
(function(){
var NH="__NHOM__",R=document.getElementById("gdcot-"+NH);if(!R){return}
function Q(k){return R.querySelector('[data-r="'+k+'"]')}
function nf(n){return Number(n).toLocaleString("vi-VN")}
function sg(n){return (n>0?"+":"")+nf(n)}
function cl(n){return n>0?"up":(n<0?"dn":"")}
function dm(s){return s.slice(8,10)+"/"+s.slice(5,7)+"/"+s.slice(0,4)}
fetch("/index.php/wp-json/wp/v2/pages?slug=du-lieu-cot").then(function(r){return r.json()}).then(function(a){
var doc=new DOMParser().parseFromString(a[0].content.rendered,"text/html");var D=JSON.parse(doc.getElementById("gd-data").textContent);
var SP=D.sp.filter(function(s){return s[2]===NH});if(!SP.length){Q("sum").textContent="Chưa có số liệu COT cho nhóm này.";return}
var cur=SP[0][0];
function btn(){var b=Q("btn");b.innerHTML="";SP.forEach(function(s){var e=document.createElement("button");e.type="button";e.textContent=s[1];if(s[0]===cur){e.className="on"}e.onclick=function(){cur=s[0];btn();ve()};b.appendChild(e)})}
function ve(){
var x=D.d[cur],n=x.d.length,i=n-1,t=SP.filter(function(s){return s[0]===cur})[0][1];
var mm=x.mml.map(function(v,k){return v-x.mms[k]}),pm=x.pml.map(function(v,k){return v-x.pms[k]}),sw=x.swl.map(function(v,k){return v-x.sws[k]});
var or_=x.orl.map(function(v,k){return v-x.ors[k]}),nr=x.nrl.map(function(v,k){return v-x.nrs[k]});
var mx=Math.max.apply(null,mm),mn=Math.min.apply(null,mm),pct=mx===mn?50:Math.round((mm[i]-mn)/(mx-mn)*100);
var s="Tuần chốt "+dm(x.d[i])+": quỹ đầu cơ "+(mm[i]>=0?"mua ròng ":"bán ròng ")+nf(Math.abs(mm[i]))+" hợp đồng "+t+" (tuần trước "+sg(mm[i]-mm[i-1])+")";
s+=", nằm ở mức "+pct+"% trong biên độ 2 năm (0% là thấp nhất, 100% là cao nhất). Nhà sản xuất, thương mại ròng "+sg(pm[i])+". Tổng hợp đồng mở "+nf(x.oi[i])+" ("+sg(x.oi[i]-x.oi[i-1])+").";
Q("sum").textContent=s;
var W=Q("ch").getBoundingClientRect().width||700;if(W>860){W=860}var H=W<600?220:280,L=W<600?50:62,Rr=8,T=10,B=26,pw=W-L-Rr,ph=H-T-B;
var all=mm.concat(pm,sw),hi=Math.max.apply(null,all),lo=Math.min.apply(null,all);if(lo>0){lo=0}if(hi<0){hi=0}
var sp=(hi-lo)/4,p=Math.pow(10,Math.floor(Math.log(sp)/Math.LN10)),st=Math.ceil(sp/p)*p;hi=Math.ceil(hi/st)*st;lo=Math.floor(lo/st)*st;
function Y(v){return T+(hi-v)/(hi-lo)*ph}function X(k){return L+(k+0.5)/n*pw}
var o='<svg viewBox="0 0 '+W+' '+H+'" xmlns="http://www.w3.org/2000/svg" font-size="11" fill="#555">';
for(var g=lo;g<=hi+st/2;g+=st){o+='<line x1="'+L+'" x2="'+(W-Rr)+'" y1="'+Y(g).toFixed(1)+'" y2="'+Y(g).toFixed(1)+'" stroke="'+(g===0?"#999":"#eee")+'"/><text x="'+(L-5)+'" y="'+(Y(g)+4).toFixed(1)+'" text-anchor="end">'+(Math.abs(g)>=1000?nf(Math.round(g/1000))+"K":nf(g))+'</text>'}
var bw=Math.max(1,pw/n-1);mm.forEach(function(v,k){var y1=Y(Math.max(v,0)),y2=Y(Math.min(v,0));o+='<rect x="'+(X(k)-bw/2).toFixed(1)+'" y="'+y1.toFixed(1)+'" width="'+bw.toFixed(1)+'" height="'+Math.max(0.5,y2-y1).toFixed(1)+'" fill="#2f6db3" opacity="0.85"><title>'+dm(x.d[k])+": "+sg(v)+'</title></rect>'});
function ln(a,c){var d="";a.forEach(function(v,k){d+=(k?"L":"M")+X(k).toFixed(1)+" "+Y(v).toFixed(1)+" "});return '<path d="'+d+'" fill="none" stroke="'+c+'" stroke-width="1.6"/>'}
o+=ln(pm,"#8a8080")+ln(sw,"#e0a100");
[0,Math.floor(n/2),n-1].forEach(function(k){o+='<text x="'+X(k).toFixed(1)+'" y="'+(H-8)+'" text-anchor="'+(k===0?"start":(k===n-1?"end":"middle"))+'">'+dm(x.d[k])+'</text>'});
Q("ch").innerHTML=o+"</svg>";
var rows=[["Quỹ đầu cơ (Managed Money)",x.mml,x.mms],["Nhà sản xuất, thương mại",x.pml,x.pms],["Swap dealer",x.swl,x.sws],["Tổ chức khác",x.orl,x.ors],["Nhỏ lẻ (không báo cáo)",x.nrl,x.nrs]];
var h='<table><tr><th>Nhóm</th><th>Mua</th><th>Bán</th><th>Ròng</th><th>Thay đổi ròng 1 tuần</th><th>% hợp đồng mở</th></tr>';
rows.forEach(function(r){var nt=r[1][i]-r[2][i],nt0=r[1][i-1]-r[2][i-1];h+="<tr><td>"+r[0]+"</td><td>"+nf(r[1][i])+"</td><td>"+nf(r[2][i])+'</td><td class="'+cl(nt)+'">'+sg(nt)+'</td><td class="'+cl(nt-nt0)+'">'+sg(nt-nt0)+"</td><td>"+(x.oi[i]?Math.round((r[1][i]+r[2][i])/2/x.oi[i]*100):0)+"%</td></tr>"});
Q("tb").innerHTML=h+"</table>"}
btn();ve();var rz;window.addEventListener("resize",function(){clearTimeout(rz);rz=setTimeout(ve,150)})
}).catch(function(){Q("sum").textContent="Chưa tải được số liệu COT, bạn vui lòng tải lại trang."})})();
</script>
<!-- /wp:html -->
'''
