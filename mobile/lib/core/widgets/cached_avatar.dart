import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

/// Network-backed avatar with initial-letter fallback.
///
/// Sized to a fixed width × height so the layout never jumps while the
/// image loads or fails. The placeholder and error widget render the
/// same initial-letter bubble, giving a visually consistent avatar
/// before, during, and after the image fetch.
///
/// ### Usage
/// ```dart
/// CachedAvatar(
///   url: user.avatarUrl,           // null → render fallback only
///   fallbackInitial: user.name[0], // single character
///   size: 40,
/// );
/// ```
///
/// ### Performance
/// - Uses [CachedNetworkImage] so images are stored on disk after the
///   first download. Subsequent opens render from local cache in <5ms.
/// - The placeholder is identical to the error widget, so the avatar
///   never flickers between two different fallback shapes.
/// - A `memCacheWidth` of `size × 3` decodes the image at 3× for hi-dpi
///   screens, avoiding the GPU having to upscale a low-res bitmap.
class CachedAvatar extends StatelessWidget {
  const CachedAvatar({
    super.key,
    required this.url,
    required this.fallbackInitial,
    this.size = 40,
    this.backgroundAlpha = 0.08,
  });

  /// The network URL of the avatar. Pass `null` (or empty) to render
  /// the initial-letter fallback only — useful for users without a
  /// Discord avatar, or as the placeholder/error state.
  final String? url;

  /// The character to display in the initial-letter fallback.
  final String fallbackInitial;

  /// Width and height of the avatar (in logical pixels). Always
  /// rendered as a square.
  final double size;

  /// Alpha of the placeholder bubble's primary-tinted background.
  final double backgroundAlpha;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final placeholder = _InitialBubble(
      initial: fallbackInitial,
      size: size,
      color: colorScheme.primary,
      backgroundAlpha: backgroundAlpha,
    );

    // No URL — render the fallback only.
    if (url == null || url!.isEmpty) return placeholder;

    return ClipOval(
      child: CachedNetworkImage(
        imageUrl: url!,
        width: size,
        height: size,
        fit: BoxFit.cover,
        // 3× for hi-dpi screens (avoids GPU upscaling).
        memCacheWidth: (size * 3).toInt(),
        fadeInDuration: const Duration(milliseconds: 150),
        placeholder: (_, _) => placeholder,
        errorWidget: (_, _, _) => placeholder,
      ),
    );
  }
}

// =============================================================================
// Internal — initial-letter bubble (matches existing avatar look in
//            _UserProfileSheet and _LeaderboardRow).
// =============================================================================

class _InitialBubble extends StatelessWidget {
  const _InitialBubble({
    required this.initial,
    required this.size,
    required this.color,
    required this.backgroundAlpha,
  });

  final String initial;
  final double size;
  final Color color;
  final double backgroundAlpha;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: color.withValues(alpha: backgroundAlpha),
        shape: BoxShape.circle,
      ),
      child: Center(
        child: Text(
          initial.isEmpty ? '?' : initial.toUpperCase(),
          style: TextStyle(
            fontSize: size * 0.4,
            fontWeight: FontWeight.w800,
            color: color,
          ),
        ),
      ),
    );
  }
}
