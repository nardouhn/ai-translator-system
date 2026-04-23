import 'package:flutter/material.dart';

class SidebarQueueWidget extends StatelessWidget {
  const SidebarQueueWidget({
    super.key,
    required this.queue,
    required this.onDownload,
    required this.onDelete,
  });

  final List<Map<String, dynamic>> queue;
  final Function(int) onDownload;
  final Function(int) onDelete;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Column(
        children: [
          if (queue.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 32),
              child: Text(
                'No items in queue',
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
                  fontStyle: FontStyle.italic,
                ),
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: queue.length,
              separatorBuilder: (context, index) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                final item = queue[index];
                return QueueItemCard(
                  fileName: item['fileName'],
                  fileType: item['fileType'],
                  fileSize: item['fileSize'],
                  status: item['status'],
                  progress: item['progress'],
                  onDownload: () => onDownload(index),
                  onDelete: () => onDelete(index),
                );
              },
            ),
          const SizedBox(height: 16),
          const TipCard(),
        ],
      ),
    );
  }
}

class QueueItemCard extends StatelessWidget {
  const QueueItemCard({
    super.key,
    required this.fileName,
    required this.fileType,
    required this.fileSize,
    required this.status,
    required this.progress,
    required this.onDownload,
    required this.onDelete,
  });

  final String fileName;
  final String fileType;
  final String fileSize;
  final String status;
  final double progress;
  final VoidCallback onDownload;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final primaryColor = Theme.of(context).colorScheme.primary;
    final onSurface = Theme.of(context).colorScheme.onSurface;
    final surfaceColor = Theme.of(context).colorScheme.surface;

    IconData fileIcon;
    Color iconColor;
    if (fileType.toLowerCase() == 'pdf') {
      fileIcon = Icons.picture_as_pdf;
      iconColor = Colors.redAccent;
    } else if (fileType.toLowerCase() == 'docx') {
      fileIcon = Icons.description;
      iconColor = Colors.blueAccent;
    } else {
      fileIcon = Icons.text_snippet;
      iconColor = Colors.grey;
    }

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: surfaceColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: primaryColor.withOpacity(0.1)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: iconColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(fileIcon, color: iconColor, size: 24),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  fileName,
                  style: TextStyle(
                    color: onSurface,
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Text(
                      fileSize,
                      style: TextStyle(
                        color: onSurface.withOpacity(0.6),
                        fontSize: 12,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      width: 4,
                      height: 4,
                      decoration: BoxDecoration(
                        color: onSurface.withOpacity(0.3),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        status,
                        style: TextStyle(
                          color: progress == 1.0 ? Colors.green : primaryColor,
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                if (progress > 0 && progress < 1.0) ...[
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: progress,
                      backgroundColor: primaryColor.withOpacity(0.1),
                      valueColor: AlwaysStoppedAnimation<Color>(primaryColor),
                      minHeight: 4,
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 8),
          if (progress == 1.0)
            IconButton(
              icon: Icon(Icons.download, color: primaryColor),
              onPressed: onDownload,
              tooltip: 'Download translated file',
            )
          else if (progress == 0.0)
            IconButton(
              icon: const Icon(Icons.delete_outline, color: Colors.redAccent),
              onPressed: onDelete,
              tooltip: 'Delete file',
            )
          else
            IconButton(
              icon: Icon(Icons.more_vert, color: onSurface.withOpacity(0.5)),
              onPressed: () {},
            ),
        ],
      ),
    );
  }
}

class TipCard extends StatelessWidget {
  const TipCard({super.key});

  @override
  Widget build(BuildContext context) {
    final primaryColor = Theme.of(context).colorScheme.primary;
    final onSurface = Theme.of(context).colorScheme.onSurface;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: primaryColor.withOpacity(0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: primaryColor.withOpacity(0.2)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.lightbulb_outline, color: primaryColor, size: 24),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "Tip from the Architect",
                  style: TextStyle(
                    color: primaryColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  "To get the best layout preservation, ensure your document uses standard fonts and clear paragraph structures.",
                  style: TextStyle(
                    color: onSurface.withOpacity(0.8),
                    fontSize: 13,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
