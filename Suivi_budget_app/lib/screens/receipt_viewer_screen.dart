import 'package:flutter/material.dart';

class ReceiptViewerScreen extends StatelessWidget {
  final String imageUrl;
  final String title;

  const ReceiptViewerScreen({
    super.key,
    required this.imageUrl,
    required this.title,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text(
          title,
          style: const TextStyle(fontSize: 16),
        ),
      ),
      body: Center(
        child: InteractiveViewer(
          panEnabled: true,
          minScale: 0.5,
          maxScale: 4.0,
          child: Image.network(
            imageUrl,
            fit: BoxFit.contain,
            loadingBuilder: (context, child, loadingProgress) {
              if (loadingProgress == null) return child;
              return Center(
                child: CircularProgressIndicator(
                  value: loadingProgress.expectedTotalBytes != null
                      ? loadingProgress.cumulativeBytesLoaded /
                          loadingProgress.expectedTotalBytes!
                      : null,
                  color: Colors.white,
                ),
              );
            },
            errorBuilder: (context, error, stackTrace) {
              return const Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.broken_image_rounded, size: 64, color: Colors.white54),
                  SizedBox(height: 12),
                  Text(
                    'Impossible de charger l\'image du reçu',
                    style: TextStyle(color: Colors.white70),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}
