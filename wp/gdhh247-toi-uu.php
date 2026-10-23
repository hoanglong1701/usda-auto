<?php
/**
 * Plugin Name: GDHH247 – Tối ưu hiệu năng & SEO
 * Description: Bỏ tài nguyên thừa cho khách, sửa schema/H1, noindex trang dữ liệu, shortcode tin mới render phía server.
 * Version: 1.4.0
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

/* Trang dữ liệu ẩn: noindex + X-Robots-Tag (phòng khi Rank Math bị đổi cấu hình). */
add_action( 'template_redirect', function () {
	if ( is_page( GDHH_DATA_PAGES ) ) {
		header( 'X-Robots-Tag: noindex, nofollow', true );
	}
} );

/* Rank Math: trang dữ liệu ẩn luôn noindex trong thẻ meta (khớp với X-Robots-Tag ở trên). */
add_filter( 'rank_math/frontend/robots', function ( $robots ) {
	if ( is_page( GDHH_DATA_PAGES ) ) {
		$robots['index']  = 'noindex';
		$robots['follow'] = 'nofollow';
	}
	return $robots;
} );

/* Trang cũ 32–35 chỉ có 1 câu "đang hoàn thiện": chuyển hướng 301 sang trang phân tích tương ứng. */
const GDHH_REDIRECTS = array( 32 => 300, 33 => 299, 34 => 301, 35 => 302 );

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
		$skip = array_merge( GDHH_DATA_PAGES, array_keys( GDHH_REDIRECTS ), array( 2 ) );
		if ( in_array( (int) $object->ID, $skip, true ) ) {
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
