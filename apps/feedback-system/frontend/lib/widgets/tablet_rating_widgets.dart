import 'package:flutter/material.dart';

/// Tablet-optimized rating bar (1-5 scale)
/// Large touch targets with visual feedback
class TabletRatingBar extends StatefulWidget {
  final String label;
  final String? icon;
  final int? initialRating;
  final ValueChanged<int> onRatingSelected;
  final Color? activeColor;
  final int maxRating;

  const TabletRatingBar({
    super.key,
    required this.label,
    this.icon,
    this.initialRating,
    required this.onRatingSelected,
    this.activeColor,
    this.maxRating = 5,
  });

  @override
  State<TabletRatingBar> createState() => _TabletRatingBarState();
}

class _TabletRatingBarState extends State<TabletRatingBar> {
  int? selectedRating;

  @override
  void initState() {
    super.initState();
    selectedRating = widget.initialRating;
  }

  @override
  Widget build(BuildContext context) {
    final activeColor = widget.activeColor ?? Theme.of(context).primaryColor;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Label with icon
        Row(
          children: [
            if (widget.icon != null) ...[
              Text(
                widget.icon!,
                style: const TextStyle(fontSize: 28),
              ),
              const SizedBox(width: 12),
            ],
            Expanded(
              child: Text(
                widget.label,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            if (selectedRating != null)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: activeColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: activeColor, width: 2),
                ),
                child: Text(
                  '$selectedRating/${widget.maxRating}',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: activeColor,
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: 16),

        // Rating buttons
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: List.generate(widget.maxRating, (index) {
            final rating = index + 1;
            final isSelected = selectedRating == rating;

            return _RatingButton(
              rating: rating,
              isSelected: isSelected,
              activeColor: activeColor,
              onTap: () {
                setState(() {
                  selectedRating = rating;
                });
                widget.onRatingSelected(rating);
              },
            );
          }),
        ),
      ],
    );
  }
}

class _RatingButton extends StatelessWidget {
  final int rating;
  final bool isSelected;
  final Color activeColor;
  final VoidCallback onTap;

  const _RatingButton({
    required this.rating,
    required this.isSelected,
    required this.activeColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: isSelected ? activeColor : Colors.white,
      borderRadius: BorderRadius.circular(12),
      elevation: isSelected ? 4 : 1,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isSelected ? activeColor : Colors.grey[300]!,
              width: isSelected ? 3 : 2,
            ),
          ),
          child: Center(
            child: Text(
              '$rating',
              style: TextStyle(
                fontSize: 32,
                fontWeight: FontWeight.bold,
                color: isSelected ? Colors.white : Colors.grey[700],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Tablet-optimized smiley picker (5 levels)
/// Visual feedback system with emojis
class TabletSmileyPicker extends StatefulWidget {
  final String label;
  final String? icon;
  final int? initialValue;
  final ValueChanged<int> onSelected;
  final Color? activeColor;

  const TabletSmileyPicker({
    super.key,
    required this.label,
    this.icon,
    this.initialValue,
    required this.onSelected,
    this.activeColor,
  });

  @override
  State<TabletSmileyPicker> createState() => _TabletSmileyPickerState();
}

class _TabletSmileyPickerState extends State<TabletSmileyPicker> {
  int? selectedValue;

  static const List<String> smileys = ['😞', '😕', '😐', '🙂', '😊'];
  static const List<String> labels = ['Very Poor', 'Poor', 'Average', 'Good', 'Excellent'];
  static const List<Color> colors = [
    Color(0xFFE74C3C), // Red
    Color(0xFFE67E22), // Orange
    Color(0xFFF39C12), // Yellow
    Color(0xFF2ECC71), // Light Green
    Color(0xFF27AE60), // Green
  ];

  @override
  void initState() {
    super.initState();
    selectedValue = widget.initialValue;
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Label with icon
        Row(
          children: [
            if (widget.icon != null) ...[
              Text(
                widget.icon!,
                style: const TextStyle(fontSize: 28),
              ),
              const SizedBox(width: 12),
            ],
            Expanded(
              child: Text(
                widget.label,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            if (selectedValue != null)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: colors[selectedValue! - 1].withOpacity(0.1),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: colors[selectedValue! - 1], width: 2),
                ),
                child: Text(
                  labels[selectedValue! - 1],
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: colors[selectedValue! - 1],
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: 16),

        // Smiley buttons
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: List.generate(5, (index) {
            final value = index + 1;
            final isSelected = selectedValue == value;

            return _SmileyButton(
              smiley: smileys[index],
              label: labels[index],
              color: colors[index],
              isSelected: isSelected,
              onTap: () {
                setState(() {
                  selectedValue = value;
                });
                widget.onSelected(value);
              },
            );
          }),
        ),
      ],
    );
  }
}

class _SmileyButton extends StatelessWidget {
  final String smiley;
  final String label;
  final Color color;
  final bool isSelected;
  final VoidCallback onTap;

  const _SmileyButton({
    required this.smiley,
    required this.label,
    required this.color,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeInOut,
        width: isSelected ? 120 : 100,
        height: isSelected ? 120 : 100,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected ? color : Colors.grey[300]!,
            width: isSelected ? 4 : 2,
          ),
          boxShadow: [
            BoxShadow(
              color: isSelected ? color.withOpacity(0.3) : Colors.black.withOpacity(0.1),
              blurRadius: isSelected ? 12 : 8,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              smiley,
              style: TextStyle(fontSize: isSelected ? 52 : 48),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: isSelected ? 13 : 11,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                color: isSelected ? color : Colors.grey[600],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Tablet-optimized binary choice (Yes/No)
/// Large touch-friendly buttons
class TabletBinaryChoice extends StatefulWidget {
  final String label;
  final String? icon;
  final bool? initialValue;
  final ValueChanged<bool> onSelected;
  final String yesLabel;
  final String noLabel;
  final Color? yesColor;
  final Color? noColor;

  const TabletBinaryChoice({
    super.key,
    required this.label,
    this.icon,
    this.initialValue,
    required this.onSelected,
    this.yesLabel = 'Yes',
    this.noLabel = 'No',
    this.yesColor,
    this.noColor,
  });

  @override
  State<TabletBinaryChoice> createState() => _TabletBinaryChoiceState();
}

class _TabletBinaryChoiceState extends State<TabletBinaryChoice> {
  bool? selectedValue;

  @override
  void initState() {
    super.initState();
    selectedValue = widget.initialValue;
  }

  @override
  Widget build(BuildContext context) {
    final yesColor = widget.yesColor ?? const Color(0xFF27AE60);
    final noColor = widget.noColor ?? const Color(0xFFE74C3C);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Label with icon
        Row(
          children: [
            if (widget.icon != null) ...[
              Text(
                widget.icon!,
                style: const TextStyle(fontSize: 28),
              ),
              const SizedBox(width: 12),
            ],
            Expanded(
              child: Text(
                widget.label,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Yes/No buttons
        Row(
          children: [
            Expanded(
              child: _BinaryChoiceButton(
                label: widget.yesLabel,
                icon: Icons.thumb_up_rounded,
                color: yesColor,
                isSelected: selectedValue == true,
                onTap: () {
                  setState(() {
                    selectedValue = true;
                  });
                  widget.onSelected(true);
                },
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: _BinaryChoiceButton(
                label: widget.noLabel,
                icon: Icons.thumb_down_rounded,
                color: noColor,
                isSelected: selectedValue == false,
                onTap: () {
                  setState(() {
                    selectedValue = false;
                  });
                  widget.onSelected(false);
                },
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _BinaryChoiceButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color color;
  final bool isSelected;
  final VoidCallback onTap;

  const _BinaryChoiceButton({
    required this.label,
    required this.icon,
    required this.color,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: isSelected ? color : Colors.white,
      borderRadius: BorderRadius.circular(16),
      elevation: isSelected ? 6 : 2,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          height: 100,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: isSelected ? color : Colors.grey[300]!,
              width: isSelected ? 3 : 2,
            ),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                icon,
                size: 40,
                color: isSelected ? Colors.white : color,
              ),
              const SizedBox(height: 8),
              Text(
                label,
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: isSelected ? Colors.white : Colors.grey[700],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
