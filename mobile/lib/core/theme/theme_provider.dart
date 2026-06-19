import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Manages the app's [ThemeMode] (light / dark / system) and persists the
/// user's choice to [SharedPreferences].
///
/// Register via [ChangeNotifierProvider] in the widget tree and call [init]
/// once at startup to restore the persisted preference.
class ThemeProvider extends ChangeNotifier {
  ThemeProvider();

  static const _prefsKey = 'app_theme_mode';

  ThemeMode _themeMode = ThemeMode.light;

  /// The current theme mode used by [MaterialApp.themeMode].
  ThemeMode get themeMode => _themeMode;

  /// Reads the persisted theme preference from [SharedPreferences].
  ///
  /// Defaults to [ThemeMode.light] when no value has been stored yet.
  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    final stored = prefs.getString(_prefsKey);

    _themeMode = switch (stored) {
      'dark'   => ThemeMode.dark,
      'system' => ThemeMode.system,
      _        => ThemeMode.light,
    };

    notifyListeners();
  }

  /// Updates the theme mode, persists the choice, and notifies listeners.
  Future<void> setThemeMode(ThemeMode mode) async {
    if (_themeMode == mode) return;

    _themeMode = mode;
    notifyListeners();

    final prefs = await SharedPreferences.getInstance();
    final value = switch (mode) {
      ThemeMode.dark   => 'dark',
      ThemeMode.system => 'system',
      ThemeMode.light  => 'light',
    };
    await prefs.setString(_prefsKey, value);
  }
}
