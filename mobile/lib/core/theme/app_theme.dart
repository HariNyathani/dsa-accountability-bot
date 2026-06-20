import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Immutable design-system container for the DSA Accountability app.
///
/// Exposes [lightTheme] and [darkTheme] as static, compile-time–safe
/// [ThemeData] instances built on Material 3 conventions.
///
/// Color palette philosophy:
///   • Light — Premium minimalist beige / editorial journal aesthetic.
///   • Dark  — Pure AMOLED black with luminous neon accents.
final class AppTheme {
  const AppTheme._(); // Prevent instantiation.

  // ---------------------------------------------------------------------------
  // ☀️  LIGHT MODE PALETTE
  // ---------------------------------------------------------------------------
  static const Color _lightScaffold     = Color(0xFFF2E2DE); // Ultra-light Alabaster Porcelain Beige
  static const Color _lightSurface      = Color(0xFFF2E2DE); // Ultra-light Alabaster Porcelain Beige
  static const Color _lightPrimary      = Color(0xFF7A5234); // Deep Chestnut Espresso
  static const Color _lightOnPrimary    = Color(0xFFFFFFFF);
  static const Color _lightTextPrimary  = Color(0xFF3E2723); // Deep rich brown
  static const Color _lightTextSecondary = Color(0xFF706A60); // Stone gray
  static const Color _lightBorder       = Color(0x1A1C1A17); // ~10 % opacity

  // ---------------------------------------------------------------------------
  // 🌙  DARK MODE PALETTE
  // ---------------------------------------------------------------------------
  static const Color _darkScaffold      = Color(0xFF0A0B10); // Deep obsidian
  static const Color _darkSurface       = Color(0xFF0D0D12); // Dark charcoal
  static const Color _darkPrimary       = Color(0xFF7A5234); // Deep Chestnut Espresso
  static const Color _darkOnPrimary     = Color(0xFFFFFFFF);
  static const Color _darkTextPrimary   = Color(0xFFFFFFFF);
  static const Color _darkTextSecondary = Color(0xFF9E9E9E); // Slate gray
  static const Color _darkBorder        = Color(0x1AFFFFFF); // ~10 % opacity

  // ---------------------------------------------------------------------------
  // 📐  GEOMETRY TOKENS
  // ---------------------------------------------------------------------------
  static const double cardRadius   = 32.0;
  static const double buttonRadius = 24.0;
  static const double borderWidth  = 0.5;

  // ---------------------------------------------------------------------------
  // THEMES
  // ---------------------------------------------------------------------------

  /// Premium minimalist beige — the system default.
  static ThemeData get lightTheme {
    final base = ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
    );

    final textTheme = GoogleFonts.plusJakartaSansTextTheme(base.textTheme)
        .apply(
          bodyColor: _lightTextPrimary,
          displayColor: _lightTextPrimary,
        );

    return base.copyWith(
      scaffoldBackgroundColor: _lightScaffold,
      colorScheme: ColorScheme.light(
        primary: _lightPrimary,
        onPrimary: _lightOnPrimary,
        secondary: _lightPrimary,
        onSecondary: _lightOnPrimary,
        surface: _lightSurface,
        onSurface: _lightTextPrimary,
        onSurfaceVariant: _lightTextSecondary,
        outline: _lightBorder,
        outlineVariant: _lightBorder,
        error: const Color(0xFFBA1A1A),
        onError: Colors.white,
      ),
      textTheme: textTheme,
      cardTheme: CardThemeData(
        color: _lightSurface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(cardRadius),
          side: const BorderSide(
            color: _lightBorder,
            width: borderWidth,
          ),
        ),
        clipBehavior: Clip.antiAlias,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: _lightPrimary,
          foregroundColor: _lightOnPrimary,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(buttonRadius),
          ),
          textStyle: GoogleFonts.plusJakartaSans(
            fontWeight: FontWeight.w600,
            fontSize: 15,
            letterSpacing: 0.2,
          ),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: _lightPrimary,
          foregroundColor: _lightOnPrimary,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(buttonRadius),
          ),
          textStyle: GoogleFonts.plusJakartaSans(
            fontWeight: FontWeight.w600,
            fontSize: 15,
            letterSpacing: 0.2,
          ),
        ),
      ),
      dividerTheme: const DividerThemeData(
        color: _lightBorder,
        thickness: borderWidth,
        space: 0,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: _lightScaffold,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: true,
        titleTextStyle: GoogleFonts.plusJakartaSans(
          color: _lightTextPrimary,
          fontWeight: FontWeight.w700,
          fontSize: 18,
          letterSpacing: -0.3,
        ),
        iconTheme: const IconThemeData(color: _lightTextPrimary, size: 22),
      ),
      iconTheme: const IconThemeData(color: _lightTextSecondary, size: 22),
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: _lightScaffold,
        selectedItemColor: _lightPrimary,
        unselectedItemColor: _lightTextSecondary,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
        selectedLabelStyle: GoogleFonts.plusJakartaSans(
          fontWeight: FontWeight.w600,
          fontSize: 11,
        ),
        unselectedLabelStyle: GoogleFonts.plusJakartaSans(
          fontWeight: FontWeight.w500,
          fontSize: 11,
        ),
      ),
    );
  }

  /// AMOLED dark mode — pure black with neon accents.
  static ThemeData get darkTheme {
    final base = ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
    );

    final textTheme = GoogleFonts.plusJakartaSansTextTheme(base.textTheme)
        .apply(
          bodyColor: _darkTextPrimary,
          displayColor: _darkTextPrimary,
        );

    return base.copyWith(
      scaffoldBackgroundColor: _darkScaffold,
      colorScheme: ColorScheme.dark(
        primary: _darkPrimary,
        onPrimary: _darkOnPrimary,
        secondary: _darkPrimary,
        onSecondary: _darkOnPrimary,
        surface: _darkSurface,
        onSurface: _darkTextPrimary,
        onSurfaceVariant: _darkTextSecondary,
        outline: _darkBorder,
        outlineVariant: Colors.white.withValues(alpha: 0.08),
        error: const Color(0xFFFFB4AB),
        onError: const Color(0xFF690005),
      ),
      textTheme: textTheme,
      cardTheme: CardThemeData(
        color: _darkSurface,
        elevation: 16,
        shadowColor: Colors.white.withValues(alpha: 0.04),
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(cardRadius),
          side: BorderSide(
            color: Colors.white.withValues(alpha: 0.08),
            width: borderWidth,
          ),
        ),
        clipBehavior: Clip.antiAlias,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: _darkPrimary,
          foregroundColor: _darkOnPrimary,
          elevation: 12,
          shadowColor: _darkPrimary.withValues(alpha: 0.15),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(buttonRadius),
          ),
          textStyle: GoogleFonts.plusJakartaSans(
            fontWeight: FontWeight.w600,
            fontSize: 15,
            letterSpacing: 0.2,
          ),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: _darkPrimary,
          foregroundColor: _darkOnPrimary,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(buttonRadius),
          ),
          textStyle: GoogleFonts.plusJakartaSans(
            fontWeight: FontWeight.w600,
            fontSize: 15,
            letterSpacing: 0.2,
          ),
        ),
      ),
      dividerTheme: const DividerThemeData(
        color: _darkBorder,
        thickness: borderWidth,
        space: 0,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: _darkScaffold,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: true,
        titleTextStyle: GoogleFonts.plusJakartaSans(
          color: _darkTextPrimary,
          fontWeight: FontWeight.w700,
          fontSize: 18,
          letterSpacing: -0.3,
        ),
        iconTheme: const IconThemeData(color: _darkTextPrimary, size: 22),
      ),
      iconTheme: const IconThemeData(color: _darkTextSecondary, size: 22),
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: _darkScaffold,
        selectedItemColor: _darkPrimary,
        unselectedItemColor: _darkTextSecondary,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
        selectedLabelStyle: GoogleFonts.plusJakartaSans(
          fontWeight: FontWeight.w600,
          fontSize: 11,
        ),
        unselectedLabelStyle: GoogleFonts.plusJakartaSans(
          fontWeight: FontWeight.w500,
          fontSize: 11,
        ),
      ),
    );
  }
}
