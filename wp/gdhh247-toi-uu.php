<?php
/**
 * Plugin Name: GDHH247 – Tối ưu hiệu năng & SEO
 * Description: Bỏ tài nguyên thừa cho khách, sửa schema/H1, noindex trang dữ liệu, shortcode tin mới render phía server, ảnh đại diện theo chuyên mục, ảnh WebP.
 * Version: 1.5.3
 *
 * Cài đặt: chép file vào wp-content/mu-plugins/ (tạo thư mục nếu chưa có). Gỡ: xóa file.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/* Trang cần giữ tài nguyên của Paid Member Subscriptions (đăng ký, đăng nhập, tài khoản, đặt lại mật khẩu, pricing). */
const GDHH_PMS_PAGES = array( 8, 11, 13, 16, 18 );

/* Trang dữ liệu ẩn được trang hiển thị đọc qua REST. */
const GDHH_DATA_PAGES = array( 176, 177, 178, 227, 478, 801, 847, 1519, 1526 );

/* ---------------------------------------------------------------------------
 * 1. Hiệu năng: bỏ script/style không cần cho khách chưa đăng nhập
 * ------------------------------------------------------------------------- */

add_action( 'init', function () {
	foreach ( array( 'wp_head', 'wp_footer', 'wp_print_footer_scripts' ) as $hook ) {
		$p = has_action( $hook, 'print_emoji_detection_script' );
		if ( false !== $p ) {
			remove_action( $hook, 'print_emoji_detection_script', $p );
		}
	}
	remove_action( 'wp_print_styles', 'print_emoji_styles' );
	remove_action( 'wp_enqueue_scripts', 'wp_enqueue_emoji_styles' );
	remove_action( 'admin_print_scripts', 'print_emoji_detection_script' );
	add_filter( 'emoji_svg_url', '__return_false' );
} );

function gdhh_is_pms_page() {
	return is_page( GDHH_PMS_PAGES );
}

/* Paid Member Subscriptions nạp script ở footer (muộn hơn wp_enqueue_scripts) nên gỡ ở cả lúc in head và footer. */
function gdhh_dequeue_assets() {
	if ( is_admin() || is_user_logged_in() ) {
		return;
	}
	wp_dequeue_style( 'dashicons' );
	if ( gdhh_is_pms_page() ) {
		return;
	}
	wp_dequeue_style( 'wp-jquery-ui-dialog' );

	global $wp_scripts, $wp_styles;
	foreach ( array( $wp_scripts, $wp_styles ) as $deps ) {
		if ( ! $deps ) {
			continue;
		}
		foreach ( $deps->queue as $handle ) {
			$src = isset( $deps->registered[ $handle ] ) ? (string) $deps->registered[ $handle ]->src : '';
			if ( false !== strpos( $src, '/paid-member-subscriptions/' ) ) {
				$deps === $wp_scripts ? wp_dequeue_script( $handle ) : wp_dequeue_style( $handle );
			}
		}
	}
}
add_action( 'wp_enqueue_scripts', 'gdhh_dequeue_assets', 999 );
add_action( 'wp_print_styles', 'gdhh_dequeue_assets', 1 );
add_action( 'wp_print_footer_scripts', 'gdhh_dequeue_assets', 1 );

/* Menu trên điện thoại: Astra đặt chiều cao 100% cho dòng menu cấp 1 và CSS tùy biến (khung xổ xuống của
 * bản máy tính) cắt phần thừa, làm dòng cha cao bất thường và che mất mục con. Trả về dạng danh sách dọc gọn. */
add_action( 'wp_head', function () {
	echo '<style id="gdhh-menu-mobile">'
		. '.ast-header-break-point .main-header-menu>.menu-item>.menu-link{height:auto!important;padding-top:12px!important;padding-bottom:12px!important;line-height:1.4!important}'
		. '.ast-header-break-point .main-header-menu .menu-item{flex-direction:column;justify-content:flex-start!important}'
		. '.ast-header-break-point .main-header-menu .sub-menu{flex-shrink:0!important;overflow:visible!important;box-shadow:none!important;border:0!important;border-radius:0!important;padding:0 0 6px!important;background:transparent!important}'
		. '.ast-header-break-point .main-header-menu .sub-menu .menu-link{padding-top:9px!important;padding-bottom:9px!important;line-height:1.4!important}'
		. '.ast-header-break-point .main-header-menu .ast-menu-toggle{height:46px!important;top:0!important}'
		. '</style>';
}, 99 );

/* Watermark mờ (logo + chữ GDHH247) phủ lên mọi đồ thị, bảng số liệu, widget và ảnh lớn trong nội dung để ảnh
 * chụp màn hình luôn mang dấu GDHH247. Lớp phủ nằm trên, không nhận chuột, không đổi bố cục trang; đồ thị vẽ lại
 * bằng JS được quét lại mỗi 1,5 giây. Thêm class "gdwm-off" vào khối nào muốn bỏ watermark. */
add_action( 'wp_head', function () {
	$svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 660 400">'
		. '<g transform="translate(330 200) rotate(-24) translate(-295 -70)" fill="#6e6e6e" stroke="#6e6e6e">'
		. '<circle cx="70" cy="70" r="58" fill="none" stroke-width="12"/>'
		. '<path d="M44 96A34 34 0 1 1 98 92" fill="none" stroke-width="13"/>'
		. '<path d="M38 104L118 24" fill="none" stroke-width="11"/>'
		. '<path d="M104 12L142 0L130 38Z" stroke="none"/>'
		. '<text x="150" y="98" font-family="Arial,Helvetica,sans-serif" font-size="92" font-weight="800" stroke="none">GDHH247</text>'
		. '<text x="154" y="136" font-family="Arial,Helvetica,sans-serif" font-size="25" font-weight="700" letter-spacing="5" stroke="none">PROFESSIONAL SERVICES</text>'
		. '</g></svg>';
	echo '<style id="gdhh-watermark">'
		. '.gdwm{position:absolute;pointer-events:none;z-index:3;overflow:hidden}'
		. '.gdwm:before{content:"";position:absolute;inset:0;margin:auto;max-width:620px;max-height:380px;'
		. 'background:url("data:image/svg+xml,' . rawurlencode( $svg ) . '") center/contain no-repeat;opacity:.1}'
		. '.gdwm.gdwm-t:before{max-width:none;max-height:none;background-size:min(88%,520px) auto;background-repeat:no-repeat repeat;background-position:center 40px}'
		. '.gdwm span{position:absolute;right:6px;bottom:3px;font:600 10px/1.2 Arial,sans-serif;color:rgba(80,80,80,.45);white-space:nowrap}'
		. '@media print{.gdwm:before{opacity:.15}}'
		. '</style>';
}, 99 );

add_action( 'wp_footer', function () {
	?>
<script id="gdhh-watermark-js">(function(){
var DASH='.entry-content div[id^="gd"],.entry-content div[class^="gd"]';
var SEL=DASH+',.entry-content svg,.entry-content canvas,.entry-content iframe,.entry-content img,.entry-content table,.ast-article-single img,.ast-blog-featured-section img,.post-thumb img';
var BO='header,footer,nav,#masthead,.site-header,.site-footer,.ast-mobile-header-wrap,.gdwm,.gdwm-off,button,.wp-block-buttons';
var L=[];
function bad(e){
	if(e.closest(BO)){return true}
	var p=e.parentElement;
	if(p&&(p.closest('svg')||p.closest(DASH))){return true}
	if(e.tagName==='IMG'){var s=(e.currentSrc||e.src||'')+' '+(e.alt||'')+' '+e.className;if(/logo|icon|avatar|gravatar|emoji|qr|zalo/i.test(s)){return true}}
	if(e.tagName==='TABLE'&&e.rows.length<3){return true}
	return false;
}
function host(e){
	var p=e.parentElement;
	while(p&&p!==document.body){
		var c=getComputedStyle(p);
		if(c.position!=='static'){return p}
		if(/auto|scroll|hidden/.test(c.overflowX+c.overflowY)){p.style.position='relative';return p}
		p=p.parentElement;
	}
	return document.body;
}
function place(o){
	var e=o.e,w=o.w,r=e.getBoundingClientRect();
	if(r.width<200||r.height<110){w.style.display='none';return}
	var t,l;
	if(o.h===document.body&&getComputedStyle(document.body).position==='static'){t=r.top+window.pageYOffset;l=r.left+window.pageXOffset}
	else{var hr=o.h.getBoundingClientRect();t=r.top-hr.top-o.h.clientTop+o.h.scrollTop;l=r.left-hr.left-o.h.clientLeft+o.h.scrollLeft}
	w.style.cssText='display:block;top:'+t+'px;left:'+l+'px;width:'+r.width+'px;height:'+r.height+'px';
	w.className=r.height>600?'gdwm gdwm-t':'gdwm';
}
function scan(){
	L=L.filter(function(o){if(!o.e.isConnected){o.w.remove();return false}if(!o.w.isConnected){o.h.appendChild(o.w)}return true});
	var a=document.querySelectorAll(SEL);
	for(var i=0;i<a.length;i++){
		var e=a[i];
		if(e.__gdwm||bad(e)){continue}
		var r=e.getBoundingClientRect();
		if(r.width<200||r.height<110){continue}
		var w=document.createElement('div');w.className='gdwm';w.setAttribute('aria-hidden','true');
		w.innerHTML='<span>© GDHH247 · giaodichhanghoa247.vn</span>';
		var h=host(e);h.appendChild(w);e.__gdwm=1;L.push({e:e,w:w,h:h});
	}
	L.forEach(place);
}
var q=0;function later(){if(!q){q=1;requestAnimationFrame(function(){q=0;L.forEach(place)})}}
window.addEventListener('resize',later);
document.addEventListener('scroll',function(ev){if(ev.target!==document){later()}},true);
window.addEventListener('load',scan);
scan();setInterval(scan,1500);
})();</script>
	<?php
}, 99 );

/* Bỏ các thẻ head không cần thiết. */
remove_action( 'wp_head', 'wp_generator' );
remove_action( 'wp_head', 'rsd_link' );
remove_action( 'wp_head', 'wlwmanifest_link' );
remove_action( 'wp_head', 'wp_shortlink_wp_head' );

/* ---------------------------------------------------------------------------
 * 2. SEO
 * ------------------------------------------------------------------------- */

/* Trang chủ đang có 2 thẻ H1 ("Trang chủ" của theme + tiêu đề hero) → ẩn tiêu đề theme. */
add_filter( 'astra_the_title_enabled', function ( $enabled ) {
	return is_front_page() ? false : $enabled;
} );

/* Schema Rank Math: bài tin tức (chuyên mục 4/5/6/7) dùng NewsArticle; trang chủ không dùng Article. */
add_filter( 'rank_math/json_ld', function ( $data ) {
	foreach ( $data as $k => $entity ) {
		if ( ! is_array( $entity ) || empty( $entity['@type'] ) ) {
			continue;
		}
		if ( is_front_page() && in_array( $entity['@type'], array( 'Article', 'BlogPosting' ), true ) ) {
			unset( $data[ $k ] );
			continue;
		}
		if ( is_singular( 'post' ) && 'BlogPosting' === $entity['@type'] && has_category( array( 4, 5, 6, 7 ) ) ) {
			$data[ $k ]['@type'] = 'NewsArticle';
		}
	}
	return $data;
}, 99 );

/* Trang dữ liệu ẩn: các ID cố định ở trên, hoặc trang có slug bắt đầu bằng du-lieu- (job GitHub tự tạo, vd du-lieu-cot). */
function gdhh_is_data_page( $id = 0 ) {
	$id = $id ? (int) $id : ( is_page() ? (int) get_queried_object_id() : 0 );
	if ( ! $id ) {
		return false;
	}
	return in_array( $id, GDHH_DATA_PAGES, true )
		|| ( 'page' === get_post_type( $id ) && 0 === strpos( (string) get_post_field( 'post_name', $id ), 'du-lieu-' ) );
}

/* Trang dữ liệu ẩn: noindex + X-Robots-Tag (phòng khi Rank Math bị đổi cấu hình). */
add_action( 'template_redirect', function () {
	if ( gdhh_is_data_page() ) {
		header( 'X-Robots-Tag: noindex, nofollow', true );
	}
} );

/* Rank Math: trang dữ liệu ẩn luôn noindex trong thẻ meta (khớp với X-Robots-Tag ở trên). */
add_filter( 'rank_math/frontend/robots', function ( $robots ) {
	if ( gdhh_is_data_page() ) {
		$robots['index']  = 'noindex';
		$robots['follow'] = 'nofollow';
	}
	return $robots;
} );

/* Trang cũ 32–35 chỉ có 1 câu "đang hoàn thiện": chuyển hướng 301 sang trang phân tích tương ứng. */
const GDHH_REDIRECTS = array( 32 => 300, 33 => 299, 34 => 301, 35 => 302, 28 => 21 ); /* 28: Tin tức nhanh cũ (tĩnh, 24/9) về trang chủ */

add_action( 'template_redirect', function () {
	foreach ( GDHH_REDIRECTS as $from => $to ) {
		if ( is_page( $from ) ) {
			wp_safe_redirect( get_permalink( $to ), 301 );
			exit;
		}
	}
}, 1 );

/* Sitemap: bỏ trang dữ liệu ẩn, trang đã chuyển hướng và trang mẫu. */
add_filter( 'rank_math/sitemap/entry', function ( $url, $type, $object ) {
	if ( 'post' === $type && isset( $object->ID ) ) {
		$skip = array_merge( array_keys( GDHH_REDIRECTS ), array( 2 ) );
		if ( in_array( (int) $object->ID, $skip, true ) || gdhh_is_data_page( $object->ID ) ) {
			return false;
		}
	}
	return $url;
}, 10, 3 );

/* Tiêu đề bài viết ngắn hơn: "… - Giao Dịch Hàng Hóa 247" thành "… | GDHH247" (Google chỉ hiện khoảng 60 ký tự). */
add_filter( 'rank_math/frontend/title', function ( $title ) {
	if ( is_singular( 'post' ) ) {
		$title = preg_replace( '/\s+[-–|]\s+Giao Dịch Hàng Hóa 247$/u', ' | GDHH247', $title );
	}
	return $title;
} );

/* Chạy một lần: trang Năng lượng (302) đã có nội dung đầy đủ, cho phép Google lập chỉ mục. */
add_action( 'init', function () {
	if ( get_option( 'gdhh_seo_302' ) === '1.5.1' ) {
		return;
	}
	update_post_meta( 302, 'rank_math_title', 'Phân tích năng lượng: cung cầu dầu thô, khí tự nhiên, top 10 quốc gia' );
	update_post_meta( 302, 'rank_math_description', 'Top 10 quốc gia sản xuất, tiêu thụ, xuất nhập khẩu dầu thô và khí tự nhiên, dầu thô xuất đi đâu, báo cáo OPEC, IEA, EIA, vị thế COT và các tuyến vận chuyển năng lượng quan trọng.' );
	update_post_meta( 302, 'rank_math_robots', array( 'index' ) );
	update_option( 'gdhh_seo_302', '1.5.1', false );
	if ( class_exists( '\RankMath\Sitemap\Cache' ) ) {
		\RankMath\Sitemap\Cache::invalidate_storage();
	}
}, 21 );

/* Chạy một lần: tiêu đề, mô tả, robots cho trang 300–302 và mô tả 5 chuyên mục. Đổi khóa để chạy lại. */
add_action( 'init', function () {
	if ( get_option( 'gdhh_seo_dot1' ) === '1.4.0' ) {
		return;
	}
	$pages = array(
		300 => array( 'Phân tích kim loại: giá LME, tồn kho và cung cầu đồng, nhôm, kẽm', 'Giá và tồn kho kim loại cơ bản trên sàn LME, báo cáo cung cầu mới nhất của ICSG, IAI, ILZSG, INSG, ITA, top 10 nước sản xuất và lịch công bố báo cáo.', array( 'index' ) ),
		301 => array( 'Phân tích cà phê, đường: báo cáo cung cầu và dòng chảy thương mại', 'Báo cáo cung cầu cà phê, đường mới nhất từ USDA, ICO, CONAB, ISO, UNICA; top 10 quốc gia sản xuất, tiêu thụ 20 năm và các nước xuất khẩu đi đâu.', array( 'index' ) ),
		302 => array( 'Phân tích năng lượng: dầu thô, khí tự nhiên', 'Phân tích cung cầu và giá dầu thô, khí tự nhiên. Trang đang được hoàn thiện.', array( 'noindex' ) ),
	);
	foreach ( $pages as $id => $p ) {
		update_post_meta( $id, 'rank_math_title', $p[0] );
		update_post_meta( $id, 'rank_math_description', $p[1] );
		update_post_meta( $id, 'rank_math_robots', $p[2] );
	}
	$cats = array(
		4 => 'Tin nhanh thị trường kim loại: vàng, bạc, đồng, bạch kim, nhôm. Diễn biến giá, dữ liệu và nhận định cập nhật hằng ngày.',
		5 => 'Tin nhanh nông sản: đậu tương, ngô, lúa mì, cà phê, đường, ca cao. Báo cáo USDA, thời tiết và nhận định giá hằng ngày.',
		6 => 'Tin nhanh năng lượng: dầu thô WTI, Brent, khí tự nhiên. Tồn kho EIA, quyết định OPEC+ và nhận định giá hằng ngày.',
		7 => 'Tin vĩ mô tác động tới thị trường hàng hóa: Fed, lãi suất, đồng USD, lạm phát, số liệu kinh tế Mỹ và Trung Quốc.',
		9 => 'Khuyến nghị giao dịch hàng hóa của GDHH247: vùng vào lệnh, chốt lời, cắt lỗ, kèm phân tích tin tức, kỹ thuật và cung cầu.',
	);
	foreach ( $cats as $id => $d ) {
		if ( '' === trim( (string) term_description( $id ) ) ) {
			wp_update_term( $id, 'category', array( 'description' => $d ) );
		}
	}
	update_option( 'gdhh_seo_dot1', '1.4.0', false );
	if ( class_exists( '\RankMath\Sitemap\Cache' ) ) {
		\RankMath\Sitemap\Cache::invalidate_storage();
	}
	do_action( 'cache_enabler_clear_complete_cache' );
}, 20 );

/* Không cache trang thành viên: form đăng nhập có nonce, bản cache sẽ hết hạn sau 12–24 giờ. */
add_action( 'template_redirect', function () {
	if ( gdhh_is_pms_page() && ! defined( 'DONOTCACHEPAGE' ) ) {
		define( 'DONOTCACHEPAGE', true );
	}
} );

/* Cache Enabler chỉ xóa cache của bài và trang chuyên mục khi đăng bài; trang 112 dùng khối Latest Posts nên xóa thêm. */
add_action( 'transition_post_status', function ( $new_status, $old_status, $post ) {
	if ( 'post' === $post->post_type && ( 'publish' === $new_status || 'publish' === $old_status ) ) {
		do_action( 'cache_enabler_clear_page_cache_by_post', 112 );
	}
}, 10, 3 );

/* ---------------------------------------------------------------------------
 * 2b. Ảnh đại diện tự động cho bài chưa có ảnh: ảnh đầu tiên trong bài (biểu đồ khuyến nghị),
 *     nếu không có thì ảnh mặc định của chuyên mục (tải lên với tên gdhh247-chuyen-muc-*).
 *     Chỉ áp dụng ngoài trang quản trị, không ghi vào cơ sở dữ liệu.
 * ------------------------------------------------------------------------- */

const GDHH_CAT_THUMB = array(
	4 => 'gdhh247-chuyen-muc-kim-loai',
	5 => 'gdhh247-chuyen-muc-nong-san',
	6 => 'gdhh247-chuyen-muc-nang-luong',
	7 => 'gdhh247-chuyen-muc-vi-mo',
	9 => 'gdhh247-chuyen-muc-khuyen-nghi',
);

function gdhh_attachment_by_slug( $slug ) {
	static $cache = array();
	if ( ! isset( $cache[ $slug ] ) ) {
		$ids            = get_posts( array(
			'post_type'        => 'attachment',
			'post_status'      => 'inherit',
			'name'             => $slug,
			'fields'           => 'ids',
			'numberposts'      => 1,
			'suppress_filters' => true,
		) );
		$cache[ $slug ] = $ids ? (int) $ids[0] : 0;
	}
	return $cache[ $slug ];
}

/* _thumbnail_id thật trong cơ sở dữ liệu (đọc cache meta, không qua filter để tránh vòng lặp). */
function gdhh_real_thumb( $post_id ) {
	$meta = wp_cache_get( $post_id, 'post_meta' );
	if ( false === $meta ) {
		update_meta_cache( 'post', array( $post_id ) );
		$meta = wp_cache_get( $post_id, 'post_meta' );
	}
	return isset( $meta['_thumbnail_id'][0] ) ? (int) $meta['_thumbnail_id'][0] : 0;
}

function gdhh_auto_thumb( $post_id ) {
	$post = get_post( $post_id );
	if ( ! $post || 'post' !== $post->post_type ) {
		return 0;
	}
	if ( preg_match( '/wp-image-(\d+)/', $post->post_content, $m ) && wp_attachment_is_image( (int) $m[1] ) ) {
		return (int) $m[1];
	}
	foreach ( wp_get_post_categories( $post_id ) as $cid ) {
		if ( isset( GDHH_CAT_THUMB[ $cid ] ) ) {
			$id = gdhh_attachment_by_slug( GDHH_CAT_THUMB[ $cid ] );
			if ( $id ) {
				return $id;
			}
		}
	}
	return 0;
}

add_filter( 'get_post_metadata', function ( $value, $object_id, $meta_key, $single ) {
	if ( '_thumbnail_id' !== $meta_key || is_admin() || gdhh_real_thumb( $object_id ) ) {
		return $value;
	}
	$id = gdhh_auto_thumb( $object_id );
	if ( ! $id ) {
		return $value;
	}
	return $single ? $id : array( $id );
}, 10, 4 );

/* Ảnh tự động chỉ dùng cho danh sách bài, chia sẻ mạng xã hội, schema; không chèn banner đầu bài. */
add_filter( 'astra_featured_image_enabled', function ( $enabled ) {
	if ( is_singular( 'post' ) && ! gdhh_real_thumb( get_queried_object_id() ) ) {
		return false;
	}
	return $enabled;
} );

/* ---------------------------------------------------------------------------
 * 2c. WebP: giữ nguyên ảnh gốc JPG/PNG (bài đăng, chia sẻ không đổi), tạo thêm bản .webp cùng tên
 *     cho ảnh gốc và các cỡ thu nhỏ, rồi đổi đường dẫn trong nội dung sang .webp khi bản đó tồn tại.
 *     Ảnh cũ được chuyển dần qua WP-Cron, mỗi lượt 20 ảnh.
 * ------------------------------------------------------------------------- */

function gdhh_webp_path( $file ) {
	return preg_replace( '/\.(jpe?g|png)$/i', '.webp', $file );
}

function gdhh_make_webp( $file ) {
	$out = gdhh_webp_path( $file );
	if ( $out === $file || file_exists( $out ) || ! file_exists( $file ) ) {
		return;
	}
	$ed = wp_get_image_editor( $file );
	if ( is_wp_error( $ed ) ) {
		return;
	}
	$ed->set_quality( 80 );
	$res = $ed->save( $out, 'image/webp' );
	/* Bỏ bản WebP nếu không nhỏ hơn ảnh gốc. */
	if ( ! is_wp_error( $res ) && file_exists( $out ) && filesize( $out ) >= filesize( $file ) ) {
		@unlink( $out ); // phpcs:ignore
	}
}

function gdhh_webp_attachment( $att_id, $meta = null ) {
	$file = get_attached_file( $att_id );
	if ( ! $file || ! preg_match( '/\.(jpe?g|png)$/i', $file ) ) {
		return;
	}
	gdhh_make_webp( $file );
	$meta = $meta ? $meta : wp_get_attachment_metadata( $att_id );
	if ( ! empty( $meta['sizes'] ) ) {
		foreach ( $meta['sizes'] as $s ) {
			gdhh_make_webp( path_join( dirname( $file ), $s['file'] ) );
		}
	}
}

add_filter( 'wp_generate_attachment_metadata', function ( $meta, $att_id ) {
	if ( wp_image_editor_supports( array( 'mime_type' => 'image/webp' ) ) ) {
		gdhh_webp_attachment( $att_id, $meta );
	}
	return $meta;
}, 20, 2 );

add_filter( 'wp_content_img_tag', function ( $tag ) {
	static $up = null;
	if ( null === $up ) {
		$up = wp_get_upload_dir();
	}
	return preg_replace_callback( '#' . preg_quote( $up['baseurl'], '#' ) . '/[^"\'\s,]+\.(?:jpe?g|png)#i', function ( $m ) use ( $up ) {
		$path = $up['basedir'] . substr( $m[0], strlen( $up['baseurl'] ) );
		return file_exists( gdhh_webp_path( $path ) ) ? gdhh_webp_path( $m[0] ) : $m[0];
	}, $tag );
} );

/* Chuyển dần ảnh cũ sang WebP. */
add_action( 'init', function () {
	if ( ! wp_next_scheduled( 'gdhh_webp_batch' ) && get_option( 'gdhh_webp_done' ) !== '1' ) {
		wp_schedule_event( time() + 60, 'hourly', 'gdhh_webp_batch' );
	}
} );

add_action( 'gdhh_webp_batch', function () {
	if ( ! wp_image_editor_supports( array( 'mime_type' => 'image/webp' ) ) ) {
		return;
	}
	$last = (int) get_option( 'gdhh_webp_last', 0 );
	global $wpdb;
	$ids = $wpdb->get_col( $wpdb->prepare(
		"SELECT ID FROM {$wpdb->posts} WHERE post_type = 'attachment' AND post_mime_type IN ('image/jpeg','image/png') AND ID > %d ORDER BY ID ASC LIMIT 20",
		$last
	) );
	if ( ! $ids ) {
		update_option( 'gdhh_webp_done', '1', false );
		wp_clear_scheduled_hook( 'gdhh_webp_batch' );
		do_action( 'cache_enabler_clear_complete_cache' );
		return;
	}
	foreach ( $ids as $id ) {
		gdhh_webp_attachment( (int) $id );
	}
	update_option( 'gdhh_webp_last', (int) end( $ids ), false );
} );

/* ---------------------------------------------------------------------------
 * 3. Shortcode [gdhh_tin_moi so="30"]: danh sách tin nhanh render sẵn trong HTML
 *    (Google đọc được link nội bộ, không chờ JS). Markup trùng với ticker hiện tại.
 * ------------------------------------------------------------------------- */

add_shortcode( 'gdhh_tin_moi', function ( $atts ) {
	$atts  = shortcode_atts( array( 'so' => 30 ), $atts );
	$names = array( 4 => 'Kim loại', 5 => 'Nông sản', 6 => 'Năng lượng', 7 => 'Vĩ mô' );
	$q     = new WP_Query( array(
		'post_type'           => 'post',
		'post_status'         => 'publish',
		'category__in'        => array_keys( $names ),
		'posts_per_page'      => max( 1, min( 100, (int) $atts['so'] ) ),
		'no_found_rows'       => true,
		'ignore_sticky_posts' => true,
	) );
	if ( ! $q->have_posts() ) {
		return '<p class="gd-nl-e">Chưa có tin mới.</p>';
	}
	$out = '';
	foreach ( $q->posts as $p ) {
		$cat = '';
		foreach ( wp_get_post_categories( $p->ID ) as $cid ) {
			if ( isset( $names[ $cid ] ) ) {
				$cat = $names[ $cid ];
				break;
			}
		}
		$ts   = get_post_timestamp( $p );
		$out .= sprintf(
			'<a class="gd-nl-r" href="%s"><span class="gd-nl-t">%s</span><span class="gd-nl-d">%s</span><span class="gd-nl-k">%s</span><span class="gd-nl-h">%s</span></a>',
			esc_url( get_permalink( $p ) ),
			esc_html( wp_date( 'H:i', $ts ) ),
			esc_html( wp_date( 'd/m', $ts ) ),
			esc_html( $cat ),
			esc_html( get_the_title( $p ) )
		);
	}
	return $out;
} );
