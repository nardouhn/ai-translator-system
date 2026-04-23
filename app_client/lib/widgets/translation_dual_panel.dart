import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class TranslationDualPanel extends StatefulWidget {
  const TranslationDualPanel({
    super.key,
    this.scale = 1,
    required this.inputController,
    required this.outputText,
    required this.sourceLangName,
    required this.targetLangName,
    required this.onTranslate,
    required this.onCopy,
    required this.onSpeakSource,
    required this.onSpeakTarget,
    this.isSpeakingSource = false,
    this.isSpeakingTarget = false,
    this.isLoading = false,
  });

  final double scale;
  final TextEditingController inputController;
  final String outputText;
  final String sourceLangName;
  final String targetLangName;
  final VoidCallback onTranslate;
  final VoidCallback onCopy;
  final VoidCallback onSpeakSource;
  final VoidCallback onSpeakTarget;
  final bool isSpeakingSource;
  final bool isSpeakingTarget;
  final bool isLoading;

  @override
  State<TranslationDualPanel> createState() => _TranslationDualPanelState();
}

class _TranslationDualPanelState extends State<TranslationDualPanel> {
  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final primary = Theme.of(context).colorScheme.primary;
    final panelBgLeft = isDark ? const Color(0xFF19182B) : const Color(0xFFFAFAFA);
    final panelBgRight = isDark ? const Color(0xFF1C1B30) : const Color(0xFFEEDAF7);
    final border = isDark ? const Color(0xFF2A2740) : const Color(0xFFE7D2F3);
    final textColor = Theme.of(context).colorScheme.onSurface;

    return Container(
      width: 1500 * widget.scale,
      height: 520 * widget.scale,
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF171628) : const Color(0xFFF8ECFF),
        borderRadius: BorderRadius.circular(28 * widget.scale),
        boxShadow: [
          BoxShadow(
            color: (isDark ? const Color(0xFFAB57FF) : const Color(0xFFBE86E3))
                .withOpacity(isDark ? 0.2 : 0.35),
            blurRadius: (isDark ? 26 : 20) * widget.scale,
            spreadRadius: isDark ? 1 : 0,
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(28 * widget.scale),
        child: Stack(
          alignment: Alignment.center,
          children: [
            Row(
              children: [
                Expanded(
                  child: _EditorPane(
                    title: widget.sourceLangName,
                    subtitle: 'DETECTED',
                    footerLeft: '${widget.inputController.text.length} / 5000',
                    footerActions: [
                      GestureDetector(
                        onTap: widget.onSpeakSource,
                        child: Icon(
                          widget.isSpeakingSource ? Icons.stop_circle_outlined : Icons.volume_up_outlined,
                          color: widget.isSpeakingSource ? const Color(0xFFB23FFF) : textColor.withOpacity(0.72),
                          size: 18 * widget.scale,
                        ),
                      ),
                      Icon(Icons.mic_none_rounded, color: textColor.withOpacity(0.72), size: 18 * widget.scale),
                    ],
                    backgroundColor: panelBgLeft,
                    textColor: textColor,
                    borderColor: border,
                    scale: widget.scale,
                    content: TextField(
                      controller: widget.inputController,
                      maxLines: null,
                      minLines: null,
                      expands: true,
                      maxLength: 5000,
                      maxLengthEnforcement: MaxLengthEnforcement.enforced,
                      keyboardType: TextInputType.multiline,
                      onChanged: (value) {
                        setState(() {});
                      },
                      style: TextStyle(
                        color: textColor.withOpacity(0.9),
                        fontSize: 18 * widget.scale,
                      ),
                      decoration: InputDecoration(
                        hintText: 'Type or paste text to translate...',
                        hintStyle: TextStyle(
                          color: textColor.withOpacity(0.35),
                          fontSize: 18 * widget.scale,
                          fontWeight: FontWeight.w500,
                        ),
                        counterText: "", // Hide default counter
                        border: InputBorder.none,
                      ),
                    ),
                  ),
                ),
                Container(
                  width: 2 * widget.scale,
                  decoration: BoxDecoration(
                    color: border,
                    boxShadow: [
                      BoxShadow(
                        color: primary.withOpacity(
                          isDark ? 0.22 : 0.28,
                        ),
                        blurRadius: 18 * widget.scale,
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: _EditorPane(
                    title: widget.targetLangName,
                    subtitle: null,
                    footerLeft: '',
                    footerActions: [
                      GestureDetector(
                        onTap: widget.onSpeakTarget,
                        child: Icon(
                          widget.isSpeakingTarget ? Icons.stop_circle_outlined : Icons.volume_up_outlined,
                          color: widget.isSpeakingTarget ? const Color(0xFFB23FFF) : textColor.withOpacity(0.72),
                          size: 18 * widget.scale,
                        ),
                      ),
                      GestureDetector(
                        onTap: widget.onCopy,
                        child: Icon(Icons.copy_all_outlined, color: textColor.withOpacity(0.72), size: 18 * widget.scale),
                      ),
                      Icon(Icons.share_outlined, color: textColor.withOpacity(0.72), size: 18 * widget.scale),
                    ],
                    backgroundColor: panelBgRight,
                    textColor: textColor,
                    borderColor: border,
                    scale: widget.scale,
                    content: SingleChildScrollView(
                      child: SelectableText(
                        widget.outputText.isEmpty ? 'Translation will appear here...' : widget.outputText,
                        style: TextStyle(
                          color: widget.outputText.isEmpty 
                              ? textColor.withOpacity(0.35)
                              : textColor.withOpacity(0.9),
                          fontSize: 18 * widget.scale,
                          fontWeight: widget.outputText.isEmpty ? FontWeight.w500 : FontWeight.w400,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            GestureDetector(
              onTap: widget.isLoading ? null : widget.onTranslate,
              child: Container(
                width: 64 * widget.scale,
                height: 64 * widget.scale,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: const LinearGradient(
                    colors: [Color(0xFF8B2CFF), Color(0xFFD22DFF)],
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFFB23FFF).withOpacity(0.45),
                      blurRadius: 22 * widget.scale,
                      spreadRadius: 2,
                    ),
                  ],
                ),
                child: widget.isLoading
                    ? Center(
                        child: SizedBox(
                          width: 24 * widget.scale,
                          height: 24 * widget.scale,
                          child: CircularProgressIndicator(
                            color: Colors.white,
                            strokeWidth: 2.5 * widget.scale,
                          ),
                        ),
                      )
                    : Icon(
                        Icons.arrow_forward_rounded,
                        color: Colors.white,
                        size: 26 * widget.scale,
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _EditorPane extends StatelessWidget {
  const _EditorPane({
    required this.title,
    required this.subtitle,
    required this.footerLeft,
    required this.footerActions,
    required this.backgroundColor,
    required this.textColor,
    required this.borderColor,
    required this.scale,
    required this.content,
  });

  final String title;
  final String? subtitle;
  final String footerLeft;
  final List<Widget> footerActions;
  final Color backgroundColor;
  final Color textColor;
  final Color borderColor;
  final double scale;
  final Widget content;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: backgroundColor,
      padding: EdgeInsets.fromLTRB(
        32 * scale,
        24 * scale,
        26 * scale,
        18 * scale,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                title,
                style: TextStyle(
                  color: textColor.withOpacity(0.9),
                  fontSize: 16 * scale,
                  fontWeight: FontWeight.w700,
                ),
              ),
              if (subtitle != null) ...[
                const Spacer(),
                Row(
                  children: [
                    if (subtitle == 'DETECTED') ...[
                      Icon(
                        Icons.auto_awesome_rounded,
                        size: 14 * scale,
                        color: textColor.withOpacity(0.55),
                      ),
                      SizedBox(width: 6 * scale),
                    ],
                    Text(
                      subtitle!,
                      style: TextStyle(
                        color: textColor.withOpacity(0.5),
                        fontSize: 13 * scale,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.3,
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
          SizedBox(height: 18 * scale),
          Divider(color: borderColor, thickness: 1),
          SizedBox(height: 12 * scale),
          Expanded(child: content),
          SizedBox(height: 12 * scale),
          Row(
            children: [
              Text(
                footerLeft,
                style: TextStyle(
                  color: textColor.withOpacity(0.35),
                  fontSize: 12 * scale,
                ),
              ),
              const Spacer(),
              for (final action in footerActions) ...[
                action,
                SizedBox(width: 18 * scale),
              ],
            ],
          ),
        ],
      ),
    );
  }
}
