import 'dart:async';
import 'package:flutter/material.dart';

class FeedbackPopup extends StatefulWidget {
  final String message;
  final VoidCallback? onDismiss;

  const FeedbackPopup({
    super.key,
    required this.message,
    this.onDismiss,
  });

  @override
  State<FeedbackPopup> createState() => FeedbackPopupState();
}

class FeedbackPopupState extends State<FeedbackPopup>
    with TickerProviderStateMixin {
  late AnimationController _slideController;
  late AnimationController _fadeController;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _fadeAnimation;
  
  String _currentMessage = '';
  Timer? _dismissTimer;

  @override
  void initState() {
    super.initState();
    _currentMessage = widget.message;
    
    // Slide down animation
    _slideController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, -1),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _slideController,
      curve: Curves.easeOutCubic,
    ));
    
    // Fade animation for text changes
    _fadeController = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );
    _fadeAnimation = Tween<double>(
      begin: 1.0,
      end: 0.0,
    ).animate(_fadeController);
    
    // Start slide animation
    _slideController.forward();
    
    // Auto dismiss after 3 seconds
    _startDismissTimer();
  }
  
  void _startDismissTimer() {
    _dismissTimer?.cancel();
    _dismissTimer = Timer(const Duration(seconds: 3), () {
      if (mounted) {
        widget.onDismiss?.call();
      }
    });
  }
  
  void updateFeedback(String newMessage) {
    if (_currentMessage == newMessage) return;
    
    // Reset dismiss timer
    _startDismissTimer();
    
    // Fade out current text, update, then fade in
    _fadeController.forward().then((_) {
      if (mounted) {
        setState(() {
          _currentMessage = newMessage;
        });
        _fadeController.reverse();
      }
    });
  }

  @override
  void dispose() {
    _slideController.dispose();
    _fadeController.dispose();
    _dismissTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SlideTransition(
      position: _slideAnimation,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 20),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        decoration: BoxDecoration(
          color: Colors.black.withValues(alpha: 0.7),
          borderRadius: BorderRadius.circular(25),
          border: Border.all(
            color: Colors.white.withValues(alpha: 0.3),
            width: 1,
          ),
        ),
        child: FadeTransition(
          opacity: _fadeAnimation,
          child: Text(
            _currentMessage,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.w500,
            ),
            textAlign: TextAlign.center,
            //maxLines: 2,
            //overflow: TextOverflow.ellipsis,
          ),
        ),
      ),
    );
  }
}