import 'dart:ui';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../../core/services/haptic_service.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/spring_curve.dart';
import '../../data/models/user_stats.dart';
import '../providers/progress_provider.dart';

/// Launches the log-progress modal bottom sheet.
///
/// Call from any trigger (FAB, header button, etc.).
/// The sheet auto-refreshes dashboard data on successful submission.
///
/// **Important:** [context] must be from a widget that has
/// [ProgressProvider] as an ancestor (e.g. inside [MainShell]'s
/// `MultiProvider`). The provider instance is captured here and
/// re-provided into the modal's overlay subtree via
/// [ChangeNotifierProvider.value] so the sheet's own `context.read`
/// calls resolve correctly.
Future<void> showLogProgressSheet(BuildContext context) {
  final progressProvider = context.read<ProgressProvider>();

  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    barrierColor: Colors.black54,
    builder: (_) => ChangeNotifierProvider<ProgressProvider>.value(
      value: progressProvider,
      child: const _LogProgressSheet(),
    ),
  );
}

// =============================================================================
// Sheet widget
// =============================================================================

class _LogProgressSheet extends StatefulWidget {
  const _LogProgressSheet();

  @override
  State<_LogProgressSheet> createState() => _LogProgressSheetState();
}

class _LogProgressSheetState extends State<_LogProgressSheet>
    with SingleTickerProviderStateMixin {
  // ── Canonical topics matching the backend's resolver vocabulary ────────
  static const _topics = <String>[
    'Arrays',
    'Strings',
    'Linked List',
    'Stack',
    'Queue',
    'Trees',
    'Graphs',
    'DP',
    'Binary Search',
    'Sorting',
    'Recursion',
    'Greedy',
    'Backtracking',
    'Hashing',
    'Math',
    'Bit Manipulation',
  ];

  // ── Available platforms & difficulties ─────────────────────────────────
  static const _difficulties = <String>['Easy', 'Medium', 'Hard'];
  static const _difficultyColors = <String, Color>{
    'Easy': Color(0xFF4CAF50),
    'Medium': Color(0xFFFF9800),
    'Hard': Color(0xFFE53935),
  };

  // ── Form state ────────────────────────────────────────────────────────
  bool _isRestDay = false;
  _LogMode _logMode = _LogMode.platform;
  String? _selectedPlatform;
  String? _selectedTopic;
  String? _selectedDifficulty;
  int _questionCount = 1;
  final _problemController = TextEditingController();

  // ── SRS Confidence (1–5 stars, LeetCode only) ─────────────────────────
  // Default to 3 (Okay) so the meter is always in a valid state.
  int _confidence = 3;

  // ── Submit state machine ──────────────────────────────────────────────
  _SubmitPhase _phase = _SubmitPhase.idle;

  // ── Success check animation ───────────────────────────────────────────
  late final AnimationController _checkController;
  late final Animation<double> _checkScale;

  @override
  void initState() {
    super.initState();
    _checkController = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );
    _checkScale = CurvedAnimation(
      parent: _checkController,
      curve: Curves.elasticOut,
    );
  }

  @override
  void dispose() {
    _checkController.dispose();
    _problemController.dispose();
    super.dispose();
  }

  // ── Submission logic ──────────────────────────────────────────────────

  Future<void> _submit() async {
    if (_phase != _SubmitPhase.idle) return;

    if (_isRestDay) {
      await _submitRestDay();
    } else if (_logMode == _LogMode.platform) {
      await _submitPlatformLog();
    } else {
      await _submitSolve();
    }
  }

  Future<void> _submitRestDay() async {
    setState(() => _phase = _SubmitPhase.loading);

    try {
      final provider = context.read<ProgressProvider>();
      final res = await provider.apiClient.dio.post('/progress/rest');

      // ── Lifecycle guard ───────────────────────────────────────────────
      // Reset phase before the mounted check so an unmount during the
      // network await cannot leave the spinner permanently locked.
      if (!mounted) {
        _phase = _SubmitPhase.idle;
        return;
      }

      final data = res.data as Map<String, dynamic>?;
      final success = data?['success'] as bool? ?? false;

      if (success) {
        await HapticService.successBoom();
        setState(() => _phase = _SubmitPhase.success);
        _checkController.forward();

        // Refresh dashboard data in background.
        provider.fetchAll();

        await Future<void>.delayed(const Duration(milliseconds: 1200));
        if (mounted) Navigator.of(context).pop();
      } else {
        setState(() => _phase = _SubmitPhase.idle);
      }
    } on DioException catch (e) {
      if (!mounted) {
        _phase = _SubmitPhase.idle;
        return;
      }
      setState(() => _phase = _SubmitPhase.idle);
      final detail =
          (e.response?.data as Map<String, dynamic>?)?['detail'] as String?;
      final message = (detail != null && detail.isNotEmpty)
          ? detail
          : 'Could not log rest day. Please try again.';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(message),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      );
    }
  }

  Future<void> _submitPlatformLog() async {
    if (_selectedPlatform == null ||
        _problemController.text.trim().isEmpty) {
      return;
    }

    setState(() => _phase = _SubmitPhase.loading);

    final provider = context.read<ProgressProvider>();
    // Forward confidence only for LeetCode — the SRS system only supports
    // LeetCode problems (revision_bank references leetcode_problems FK).
    final isLeetCode = _selectedPlatform == 'LeetCode';
    final response = await provider.logPlatformProblem(
      platform: _selectedPlatform!,
      problemIdentifier: _problemController.text.trim(),
      confidence: isLeetCode ? _confidence : null,
    );

    // ── Lifecycle guard ─────────────────────────────────────────────────
    // Reset the phase BEFORE checking mounted so the state machine is
    // never stranded in _SubmitPhase.loading if the sheet was rebuilt
    // (and potentially unmounted) while the network call was in-flight.
    if (!mounted) {
      _phase = _SubmitPhase.idle;
      return;
    }

    if (response != null && response.success) {
      // ── Success flow ────────────────────────────────────────────────
      await HapticService.successBoom();

      setState(() => _phase = _SubmitPhase.success);
      _checkController.forward();

      // Show a SnackBar with the resolved problem details.
      if (response.data != null && mounted) {
        final d = response.data!;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('✅ Logged: ${d.title} [${d.difficulty}]'),
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        );
      }

      // Hold the check animation for 1.2 s, then close the sheet.
      await Future<void>.delayed(const Duration(milliseconds: 1200));
      if (mounted) Navigator.of(context).pop();
    } else {
      // ── Error flow — reset to idle so the user can retry ────────────
      setState(() => _phase = _SubmitPhase.idle);
    }
  }

  Future<void> _submitSolve() async {
    if (_selectedTopic == null) return;

    setState(() => _phase = _SubmitPhase.loading);

    final provider = context.read<ProgressProvider>();
    final request = LogProgressRequest(
      intentType: 'done',
      topics: [
        ProgressTopicLog(
          canonicalTopic: _selectedTopic!,
          questionCount: _questionCount,
          difficulty: _selectedDifficulty,
        ),
      ],
      note: _selectedPlatform != null ? 'platform:$_selectedPlatform' : null,
    );

    final response = await provider.logProgress(request);

    if (!mounted) return;

    if (response != null && response.success) {
      // ── Success flow ────────────────────────────────────────────────
      await HapticService.successBoom();

      setState(() => _phase = _SubmitPhase.success);
      _checkController.forward();

      // Hold the check animation for 1.2 s, then close the sheet.
      await Future<void>.delayed(const Duration(milliseconds: 1200));
      if (mounted) Navigator.of(context).pop();
    } else {
      // ── Error flow — reset to idle so the user can retry ────────────
      setState(() => _phase = _SubmitPhase.idle);
    }
  }

  // ── Build ─────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final isDark = theme.brightness == Brightness.dark;

    return RepaintBoundary(
      child: Padding(
        // Push above the keyboard when it's visible.
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: ClipRRect(
          borderRadius: const BorderRadius.vertical(
            top: Radius.circular(AppTheme.cardRadius), // 24 dp
          ),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 20.0, sigmaY: 20.0),
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: isDark
                      ? [
                          Colors.white.withValues(alpha: 0.05),
                          Colors.white.withValues(alpha: 0.01),
                        ]
                      : [
                          Colors.white.withValues(alpha: 0.45),
                          Colors.white.withValues(alpha: 0.15),
                        ],
                ),
                border: Border(
                  top: BorderSide(
                    color: Colors.white.withValues(alpha: isDark ? 0.15 : 0.50),
                    width: 1.0,
                  ),
                  left: BorderSide(
                    color: Colors.white.withValues(alpha: isDark ? 0.15 : 0.50),
                    width: 1.0,
                  ),
                  right: BorderSide(
                    color: Colors.white.withValues(alpha: isDark ? 0.15 : 0.50),
                    width: 1.0,
                  ),
                ),
              ),
              child: SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(24, 12, 24, 24),
                  child: SingleChildScrollView(
                    physics: const ClampingScrollPhysics(),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // ── Drag handle ─────────────────────────────────────────
                        Center(
                          child: Container(
                            width: 36,
                            height: 4,
                            margin: const EdgeInsets.only(bottom: 20),
                            decoration: BoxDecoration(
                              color: colorScheme.onSurface.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(2),
                            ),
                          ),
                        ),

                        // ── Title ───────────────────────────────────────────────
                        FittedBox(
                          fit: BoxFit.scaleDown,
                          child: Text(
                            'Log Progress',
                            style: theme.textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.w800,
                              letterSpacing: -0.3,
                            ),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'What did you work on today?',
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: colorScheme.onSurfaceVariant,
                          ),
                        ),
                        const SizedBox(height: 20),

                        // ── Intent toggle (Solve / Rest Day) ────────────────────
                        _buildIntentToggle(theme, colorScheme),
                        const SizedBox(height: 20),

                        // ── Cross-fade between Solve form and Rest Day view ─────
                        AnimatedCrossFade(
                          duration: const Duration(milliseconds: 300),
                          firstCurve: Curves.easeOut,
                          secondCurve: Curves.easeOut,
                          sizeCurve: Curves.easeInOut,
                          crossFadeState: _isRestDay
                              ? CrossFadeState.showSecond
                              : CrossFadeState.showFirst,
                          firstChild: _buildSolveForm(theme, colorScheme),
                          secondChild: _buildRestDayView(theme, colorScheme),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  // ── Intent toggle ─────────────────────────────────────────────────────

  Widget _buildIntentToggle(ThemeData theme, ColorScheme colorScheme) {
    final isDark = theme.brightness == Brightness.dark;
    final alignment = _isRestDay ? const Alignment(1.0, 0.0) : const Alignment(-1.0, 0.0);

    return Container(
      height: 44.0,
      decoration: BoxDecoration(
        color: colorScheme.onSurface.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(14.0),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(14.0),
        child: Stack(
          children: [
            AnimatedAlign(
              alignment: alignment,
              duration: const Duration(milliseconds: 350),
              curve: SpringCurve.snap,
              child: FractionallySizedBox(
                widthFactor: 0.48,
                heightFactor: 1.0,
                child: Container(
                  decoration: BoxDecoration(
                    gradient: isDark
                        ? const LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [
                              Color(0x23FFFFFF), // ~0.14 alpha — obsidian specular highlight
                              Color(0x05FFFFFF), // ~0.02 alpha — feather fade to AMOLED black
                            ],
                          )
                        : LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [
                              Colors.white.withValues(alpha: 0.60),
                              Colors.white.withValues(alpha: 0.25),
                            ],
                          ),
                    borderRadius: BorderRadius.circular(14.0),
                    border: isDark
                        ? Border.all(
                            color: Colors.white.withValues(alpha: 0.15),
                            width: 1.0,
                          )
                        : Border.all(
                            color: Colors.white.withValues(alpha: 0.65),
                            width: 0.8,
                          ),
                    boxShadow: isDark
                        ? null
                        : [
                            BoxShadow(
                              color: const Color(0xFF7A5234).withValues(alpha: 0.04),
                              blurRadius: 12,
                              offset: const Offset(0, 4),
                            ),
                          ],
                  ),
                ),
              ),
            ),
            Row(
              children: [
                _buildToggleSegment(
                  icon: Icons.code_rounded,
                  label: 'Solve',
                  isSelected: !_isRestDay,
                  onTap: () {
                    if (_isRestDay) {
                      HapticService.lightTap();
                      setState(() => _isRestDay = false);
                    }
                  },
                  theme: theme,
                ),
                _buildToggleSegment(
                  icon: Icons.bedtime_rounded,
                  label: 'Rest Day',
                  isSelected: _isRestDay,
                  onTap: () {
                    if (!_isRestDay) {
                      HapticService.lightTap();
                      setState(() => _isRestDay = true);
                    }
                  },
                  theme: theme,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildToggleSegment({
    IconData? icon,
    required String label,
    required bool isSelected,
    required VoidCallback onTap,
    required ThemeData theme,
  }) {
    return Expanded(
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: Center(
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                Icon(
                  icon,
                  size: 18,
                  color: theme.colorScheme.onSurface.withValues(alpha: isSelected ? 1.0 : 0.65),
                ),
                const SizedBox(width: 6),
              ],
              AnimatedDefaultTextStyle(
                duration: const Duration(milliseconds: 350),
                curve: SpringCurve.snap,
                style: theme.textTheme.labelMedium!.copyWith(
                  fontWeight: isSelected ? FontWeight.w800 : FontWeight.w500,
                  color: theme.colorScheme.onSurface.withValues(alpha: isSelected ? 1.0 : 0.65),
                ),
                child: Text(label),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── Solve form (mode toggle + cross-fade) ─────────────────────────────

  Widget _buildSolveForm(ThemeData theme, ColorScheme colorScheme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // ── Log mode toggle (Platform Log / Manual Log) ───────────────
        Container(
          height: 44.0,
          decoration: BoxDecoration(
            color: colorScheme.onSurface.withValues(alpha: 0.04),
            borderRadius: BorderRadius.circular(14.0),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(14.0),
            child: Stack(
              children: [
                AnimatedAlign(
                  alignment: _logMode == _LogMode.platform ? const Alignment(-1.0, 0.0) : const Alignment(1.0, 0.0),
                  duration: const Duration(milliseconds: 350),
                  curve: SpringCurve.snap,
                  child: FractionallySizedBox(
                    widthFactor: 0.48,
                    heightFactor: 1.0,
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: theme.brightness == Brightness.dark
                            ? const LinearGradient(
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                                colors: [
                                  Color(0x23FFFFFF), // ~0.14 alpha — obsidian specular highlight
                                  Color(0x05FFFFFF), // ~0.02 alpha — feather fade to AMOLED black
                                ],
                              )
                            : LinearGradient(
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                                colors: [
                                  Colors.white.withValues(alpha: 0.60),
                                  Colors.white.withValues(alpha: 0.25),
                                ],
                              ),
                        borderRadius: BorderRadius.circular(14.0),
                        border: theme.brightness == Brightness.dark
                            ? Border.all(
                                color: Colors.white.withValues(alpha: 0.15),
                                width: 1.0,
                              )
                            : Border.all(
                                color: Colors.white.withValues(alpha: 0.65),
                                width: 0.8,
                              ),
                        boxShadow: theme.brightness == Brightness.dark
                            ? null
                            : [
                                BoxShadow(
                                  color: const Color(0xFF7A5234).withValues(alpha: 0.04),
                                  blurRadius: 12,
                                  offset: const Offset(0, 4),
                                ),
                              ],
                      ),
                    ),
                  ),
                ),
                Row(
                  children: [
                    _buildToggleSegment(
                      icon: Icons.link_rounded,
                      label: 'Platform Log',
                      isSelected: _logMode == _LogMode.platform,
                      onTap: () {
                        if (_logMode != _LogMode.platform) {
                          HapticService.lightTap();
                          setState(() => _logMode = _LogMode.platform);
                        }
                      },
                      theme: theme,
                    ),
                    _buildToggleSegment(
                      icon: Icons.edit_note_rounded,
                      label: 'Manual Log',
                      isSelected: _logMode == _LogMode.manual,
                      onTap: () {
                        if (_logMode != _LogMode.manual) {
                          HapticService.lightTap();
                          setState(() => _logMode = _LogMode.manual);
                        }
                      },
                      theme: theme,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 20),

        // ── Cross-fade between Platform Log and Manual Log ────────────
        AnimatedCrossFade(
          duration: const Duration(milliseconds: 300),
          firstCurve: Curves.easeOut,
          secondCurve: Curves.easeOut,
          sizeCurve: Curves.easeInOut,
          crossFadeState: _logMode == _LogMode.platform
              ? CrossFadeState.showFirst
              : CrossFadeState.showSecond,
          firstChild: _buildPlatformLogForm(theme, colorScheme),
          secondChild: _buildManualLogForm(theme, colorScheme),
        ),
      ],
    );
  }

  // ── Platform Log form ─────────────────────────────────────────────────

  Widget _buildPlatformLogForm(ThemeData theme, ColorScheme colorScheme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // ── Platform selection chips ───────────────────────────────────
        _sectionLabel(theme, colorScheme, 'PLATFORM'),
        const SizedBox(height: 10),
        _buildPlatformChips(theme, colorScheme),
        const SizedBox(height: 20),

        // ── Question input field ──────────────────────────────────────
        _sectionLabel(theme, colorScheme, 'QUESTION'),
        const SizedBox(height: 10),
        TextField(
          controller: _problemController,
          decoration: InputDecoration(
            hintText: 'Problem #, URL, or title...',
            prefixIcon: const Icon(Icons.search_rounded, size: 20),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(color: colorScheme.outline),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(color: colorScheme.outline),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide:
                  BorderSide(color: colorScheme.primary, width: 1.5),
            ),
            contentPadding: const EdgeInsets.symmetric(
                horizontal: 16, vertical: 14),
          ),
        ),
        const SizedBox(height: 24),

        // ── Confidence Meter (LeetCode only) ────────────────────────
        // Only shown when LeetCode is selected. Hidden for Codeforces
        // and any other platform that doesn't use the revision bank.
        if (_selectedPlatform == 'LeetCode') ...[
          _buildConfidenceMeter(theme, colorScheme),
          const SizedBox(height: 24),
        ],

        // ── Submit CTA ──────────────────────────────────────────────
        // ValueListenableBuilder narrows the rebuild scope to just the submit
        // button. Without it, every keystroke in the text field would rebuild
        // the entire 1,000+ line sheet subtree.
        ValueListenableBuilder<TextEditingValue>(
          valueListenable: _problemController,
          builder: (context, textValue, _) {
            return _buildSubmitButton(
              theme: theme,
              colorScheme: colorScheme,
              isEnabled: _selectedPlatform != null &&
                  textValue.text.trim().isNotEmpty,
              label: 'Log Problem',
            );
          },
        ),
      ],
    );
  }

  // ── Confidence Meter ──────────────────────────────────────────────────

  /// Renders a row of 5 tappable star icons for the SRS confidence rating.
  ///
  /// Isolated as its own method so it can be conditionally inserted into
  /// `_buildPlatformLogForm` without touching the surrounding layout.
  /// Uses `_confidence` local state (default 3, range 1–5).
  Widget _buildConfidenceMeter(ThemeData theme, ColorScheme colorScheme) {
    const labels = [
      'Blackout',
      'Hard',
      'Okay',
      'Easy',
      'Confident',
    ];
    final starColor = const Color(0xFFF59E0B); // Amber-400 — warm gold

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        _sectionLabel(theme, colorScheme, 'CONFIDENCE'),
        const SizedBox(height: 6),
        Text(
          labels[_confidence - 1],
          style: theme.textTheme.bodySmall?.copyWith(
            color: colorScheme.onSurfaceVariant,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 10),
        Row(
          mainAxisAlignment: MainAxisAlignment.start,
          children: List.generate(5, (i) {
            final starIndex = i + 1; // 1-indexed
            final isFilled = starIndex <= _confidence;
            return GestureDetector(
              onTap: () {
                HapticService.lightTap();
                setState(() => _confidence = starIndex);
              },
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                curve: Curves.easeOut,
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                child: Icon(
                  isFilled ? Icons.star_rounded : Icons.star_border_rounded,
                  size: 32,
                  color: isFilled
                      ? starColor
                      : colorScheme.onSurface.withValues(alpha: 0.25),
                ),
              ),
            );
          }),
        ),
      ],
    );
  }

  // ── Manual Log form ───────────────────────────────────────────────────

  Widget _buildManualLogForm(ThemeData theme, ColorScheme colorScheme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // ── Topic autocomplete ────────────────────────────────────────
        _sectionLabel(theme, colorScheme, 'TOPIC'),
        const SizedBox(height: 10),
        Autocomplete<String>(
          optionsBuilder: (textEditingValue) {
            if (textEditingValue.text.isEmpty) {
              return const Iterable<String>.empty();
            }
            return _topics.where((topic) => topic
                .toLowerCase()
                .contains(textEditingValue.text.toLowerCase()));
          },
          onSelected: (selection) {
            HapticService.lightTap();
            setState(() => _selectedTopic = selection);
          },
          optionsViewOpenDirection: OptionsViewOpenDirection.down,
          fieldViewBuilder:
              (context, textController, focusNode, onFieldSubmitted) {
            return TextField(
              controller: textController,
              focusNode: focusNode,
              onSubmitted: (_) => onFieldSubmitted(),
              decoration: InputDecoration(
                hintText: 'Search topics...',
                prefixIcon: const Icon(Icons.search_rounded, size: 20),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: colorScheme.outline),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: colorScheme.outline),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide:
                      BorderSide(color: colorScheme.primary, width: 1.5),
                ),
                contentPadding: const EdgeInsets.symmetric(
                    horizontal: 16, vertical: 14),
              ),
            );
          },
          optionsViewBuilder: (context, onSelected, options) {
            final isDark = theme.brightness == Brightness.dark;
            return Align(
              alignment: Alignment.topLeft,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(16.0),
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 16.0, sigmaY: 16.0),
                  child: Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(16.0),
                      gradient: isDark
                          ? const LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: [
                                Color(0x0DFFFFFF), // 0.05
                                Color(0x02FFFFFF), // 0.01
                              ],
                            )
                          : LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: [
                                Colors.white.withValues(alpha: 0.50),
                                Colors.white.withValues(alpha: 0.20),
                              ],
                            ),
                      border: isDark
                          ? Border.all(
                              color: Colors.white.withValues(alpha: 0.15),
                              width: 0.8,
                            )
                          : Border.all(
                              color: Colors.white.withValues(alpha: 0.50),
                              width: 0.8,
                            ),
                    ),
                    child: Material(
                      color: Colors.transparent,
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxHeight: 180),
                        child: ListView.builder(
                          padding: EdgeInsets.zero,
                          shrinkWrap: true,
                          itemCount: options.length,
                          itemBuilder: (context, index) {
                            final option = options.elementAt(index);
                            final isHighlighted =
                                option == _selectedTopic;
                            return ListTile(
                              dense: true,
                              title: Text(
                                option,
                                style: theme.textTheme.bodyMedium?.copyWith(
                                  fontWeight: isHighlighted
                                      ? FontWeight.w700
                                      : FontWeight.w500,
                                  color: isHighlighted
                                      ? colorScheme.primary
                                      : theme.colorScheme.onSurface.withValues(alpha: 0.65),
                                ),
                              ),
                              onTap: () => onSelected(option),
                            );
                          },
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            );
          },
        ),

        // ── Selected topic chip ───────────────────────────────────────
        if (_selectedTopic != null) ...[
          const SizedBox(height: 12),
          Chip(
            label: Text(_selectedTopic!),
            deleteIcon: const Icon(Icons.close_rounded, size: 16),
            onDeleted: () {
              HapticService.lightTap();
              setState(() => _selectedTopic = null);
            },
            backgroundColor:
                colorScheme.primary.withValues(alpha: 0.10),
            side: BorderSide(
              color: colorScheme.primary.withValues(alpha: 0.3),
            ),
            labelStyle: theme.textTheme.bodySmall?.copyWith(
              color: colorScheme.primary,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
        const SizedBox(height: 20),

        // ── Difficulty pills ────────────────────────────────────────
        _sectionLabel(theme, colorScheme, 'DIFFICULTY'),
        const SizedBox(height: 10),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: _difficulties.map((difficulty) {
            final isSelected = difficulty == _selectedDifficulty;
            final diffColor = _difficultyColors[difficulty]!;
            return GestureDetector(
              onTap: () {
                HapticService.lightTap();
                setState(() {
                  _selectedDifficulty =
                      _selectedDifficulty == difficulty ? null : difficulty;
                });
              },
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                curve: Curves.easeOut,
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  color: isSelected
                      ? diffColor
                      : colorScheme.onSurface.withValues(alpha: 0.05),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isSelected ? diffColor : colorScheme.outline,
                    width: isSelected ? 1.5 : 0.5,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        color: isSelected ? Colors.white : diffColor,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      difficulty,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: isSelected
                            ? Colors.white
                            : colorScheme.onSurface,
                        fontWeight:
                            isSelected ? FontWeight.w700 : FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        ),
        const SizedBox(height: 20),

        // ── Question count stepper ──────────────────────────────────
        _sectionLabel(theme, colorScheme, 'QUESTIONS SOLVED'),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 8,
          ),
          decoration: BoxDecoration(
            color: colorScheme.onSurface.withValues(alpha: 0.04),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: colorScheme.outline,
              width: 0.5,
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _CounterButton(
                icon: Icons.remove_rounded,
                onTap: _questionCount > 1
                    ? () {
                        HapticService.lightTap();
                        setState(() => _questionCount--);
                      }
                    : null,
                colorScheme: colorScheme,
              ),
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 200),
                transitionBuilder: (child, animation) =>
                    ScaleTransition(
                  scale: animation,
                  child: child,
                ),
                child: Text(
                  '$_questionCount',
                  key: ValueKey(_questionCount),
                  style: theme.textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              _CounterButton(
                icon: Icons.add_rounded,
                onTap: _questionCount < 50
                    ? () {
                        HapticService.lightTap();
                        setState(() => _questionCount++);
                      }
                    : null,
                colorScheme: colorScheme,
              ),
            ],
          ),
        ),
        const SizedBox(height: 32),

        // ── Submit CTA ──────────────────────────────────────────────
        _buildSubmitButton(
          theme: theme,
          colorScheme: colorScheme,
          isEnabled: _selectedTopic != null,
          label: 'Log Progress',
        ),
      ],
    );
  }

  // ── Rest Day view ─────────────────────────────────────────────────────

  Widget _buildRestDayView(ThemeData theme, ColorScheme colorScheme) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const SizedBox(height: 12),
        Icon(
          Icons.bedtime_rounded,
          size: 48,
          color: colorScheme.primary,
        ),
        const SizedBox(height: 16),
        Text(
          'Take a breather.',
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'Your streak will be preserved.',
          style: theme.textTheme.bodySmall?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 28),
        _buildSubmitButton(
          theme: theme,
          colorScheme: colorScheme,
          isEnabled: true,
          label: 'Confirm Rest Day',
        ),
      ],
    );
  }

  // ── Shared helpers ────────────────────────────────────────────────────

  /// Builds a reusable section label (e.g. "PLATFORM", "TOPIC").
  Widget _sectionLabel(
    ThemeData theme,
    ColorScheme colorScheme,
    String text,
  ) {
    return Text(
      text,
      style: theme.textTheme.labelSmall?.copyWith(
        color: colorScheme.onSurfaceVariant,
        fontWeight: FontWeight.w700,
        letterSpacing: 1.0,
      ),
    );
  }

  /// Builds the platform selection chip row (LeetCode, Codeforces).
  Widget _buildPlatformChips(ThemeData theme, ColorScheme colorScheme) {
    _selectedPlatform ??= 'LeetCode';
    
    return Container(
      height: 44.0,
      decoration: BoxDecoration(
        color: colorScheme.onSurface.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(14.0),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(14.0),
        child: Stack(
          children: [
            AnimatedAlign(
              alignment: _selectedPlatform == 'Codeforces' ? const Alignment(1.0, 0.0) : const Alignment(-1.0, 0.0),
              duration: const Duration(milliseconds: 350),
              curve: SpringCurve.snap,
              child: FractionallySizedBox(
                widthFactor: 0.48,
                heightFactor: 1.0,
                child: Container(
                  decoration: BoxDecoration(
                    color: theme.brightness == Brightness.dark ? Colors.transparent : null,
                    gradient: theme.brightness == Brightness.dark
                        ? null
                        : LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [
                              Colors.white.withValues(alpha: 0.60),
                              Colors.white.withValues(alpha: 0.25),
                            ],
                          ),
                    borderRadius: BorderRadius.circular(14.0),
                    border: theme.brightness == Brightness.dark
                        ? Border.all(
                            color: Colors.white.withValues(alpha: 0.15),
                            width: 1.0,
                          )
                        : Border.all(
                            color: Colors.white.withValues(alpha: 0.65),
                            width: 0.8,
                          ),
                    boxShadow: theme.brightness == Brightness.dark
                        ? null
                        : [
                            BoxShadow(
                              color: const Color(0xFF7A5234).withValues(alpha: 0.04),
                              blurRadius: 12,
                              offset: const Offset(0, 4),
                            ),
                          ],
                  ),
                ),
              ),
            ),
            Row(
              children: [
                _buildToggleSegment(
                  label: 'LeetCode',
                  isSelected: _selectedPlatform == 'LeetCode',
                  onTap: () {
                    HapticService.lightTap();
                    setState(() => _selectedPlatform = 'LeetCode');
                  },
                  theme: theme,
                ),
                _buildToggleSegment(
                  label: 'Codeforces',
                  isSelected: _selectedPlatform == 'Codeforces',
                  onTap: () {
                    HapticService.lightTap();
                    setState(() => _selectedPlatform = 'Codeforces');
                  },
                  theme: theme,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }



  // ── Shared Submit CTA ─────────────────────────────────────────────────

  Widget _buildSubmitButton({
    required ThemeData theme,
    required ColorScheme colorScheme,
    required bool isEnabled,
    required String label,
  }) {
    final isDark = theme.brightness == Brightness.dark;

    return Container(
      width: double.infinity,
      height: 52,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(AppTheme.buttonRadius),
        color: !isEnabled
            ? colorScheme.onSurface.withValues(alpha: 0.08)
            : (isDark ? Colors.transparent : null),
        gradient: isEnabled && !isDark
            ? const LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color(0xFF9E6F4A),
                  Color(0xFF7A5234),
                ],
              )
            : null,
        border: isEnabled
            ? (isDark
                ? Border.all(
                    color: Colors.white.withValues(alpha: 0.15),
                    width: 1.0,
                  )
                : Border.all(
                    color: Colors.white.withValues(alpha: 0.40),
                    width: 0.8,
                  ))
            : null,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: isEnabled && _phase == _SubmitPhase.idle
              ? _submit
              : null,
          borderRadius:
              BorderRadius.circular(AppTheme.buttonRadius),
          child: Center(
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 300),
              switchInCurve: Curves.easeOut,
              switchOutCurve: Curves.easeIn,
              child: switch (_phase) {
                _SubmitPhase.idle => Text(
                    label,
                    key: const ValueKey('idle'),
                    style: theme.textTheme.titleSmall?.copyWith(
                      color: isEnabled
                          ? colorScheme.onPrimary
                          : colorScheme.onSurface
                              .withValues(alpha: 0.35),
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.2,
                    ),
                  ),
                _SubmitPhase.loading => SizedBox(
                    key: const ValueKey('loading'),
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.5,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        colorScheme.onPrimary,
                      ),
                    ),
                  ),
                _SubmitPhase.success => ScaleTransition(
                    key: const ValueKey('success'),
                    scale: _checkScale,
                    child: Icon(
                      Icons.check_rounded,
                      color: colorScheme.onPrimary,
                      size: 28,
                    ),
                  ),
              },
            ),
          ),
        ),
      ),
    );
  }
}

// =============================================================================
// Enums
// =============================================================================

enum _SubmitPhase { idle, loading, success }

enum _LogMode { platform, manual }

// =============================================================================
// Counter button
// =============================================================================

class _CounterButton extends StatelessWidget {
  const _CounterButton({
    required this.icon,
    required this.onTap,
    required this.colorScheme,
  });

  final IconData icon;
  final VoidCallback? onTap;
  final ColorScheme colorScheme;

  @override
  Widget build(BuildContext context) {
    final isEnabled = onTap != null;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: 42,
        height: 42,
        decoration: BoxDecoration(
          color: isEnabled
              ? colorScheme.primary.withValues(alpha: 0.10)
              : colorScheme.onSurface.withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(
          icon,
          size: 20,
          color: isEnabled
              ? colorScheme.primary
              : colorScheme.onSurface.withValues(alpha: 0.20),
        ),
      ),
    );
  }
}
