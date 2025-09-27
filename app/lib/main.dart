// Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license

import 'package:flutter/material.dart';
import 'package:vym/screens/camera_inference_screen.dart';
import 'package:vym/screens/login_screen.dart';

void main() {
  runApp(const VymApp());
}

class VymApp extends StatelessWidget {
  const VymApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      title: 'Vym',
      //home: LoginPage(),
      home: CameraInferenceScreen(),
    );
  }
}
