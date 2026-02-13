import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/model_provider.dart';

/// Dropdown widget for selecting an AI model per agent or per session
class ModelSelectorWidget extends StatelessWidget {
  final String agentName;
  final String currentModel;
  final bool compact;

  const ModelSelectorWidget({
    super.key,
    required this.agentName,
    required this.currentModel,
    this.compact = true,
  });

  @override
  Widget build(BuildContext context) {
    return Consumer<ModelProvider>(
      builder: (context, modelProvider, _) {
        final effectiveModel = modelProvider.getEffectiveModel(agentName, currentModel);
        final models = modelProvider.availableModels;

        if (compact) {
          return _CompactSelector(
            effectiveModel: effectiveModel,
            models: models,
            agentName: agentName,
            modelProvider: modelProvider,
          );
        }

        return _FullSelector(
          effectiveModel: effectiveModel,
          models: models,
          agentName: agentName,
          modelProvider: modelProvider,
        );
      },
    );
  }
}

class _CompactSelector extends StatelessWidget {
  final String effectiveModel;
  final List<ModelInfo> models;
  final String agentName;
  final ModelProvider modelProvider;

  const _CompactSelector({
    required this.effectiveModel,
    required this.models,
    required this.agentName,
    required this.modelProvider,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final shortName = _shortModelName(effectiveModel);
    final provider = _resolveProvider(effectiveModel);
    final icon = ModelProvider.getProviderIcon(provider);

    return PopupMenuButton<String>(
      tooltip: 'Change model ($effectiveModel)',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
          color: colorScheme.tertiaryContainer.withAlpha(120),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: colorScheme.outlineVariant.withAlpha(80)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(icon, style: const TextStyle(fontSize: 10)),
            const SizedBox(width: 3),
            Text(shortName, style: TextStyle(fontSize: 10, color: colorScheme.onTertiaryContainer, fontWeight: FontWeight.w500)),
            Icon(Icons.arrow_drop_down, size: 14, color: colorScheme.onTertiaryContainer),
          ],
        ),
      ),
      itemBuilder: (context) => models.map((m) => PopupMenuItem<String>(
        value: m.id,
        enabled: m.available,
        child: Row(
          children: [
            Text(ModelProvider.getProviderIcon(m.provider)),
            const SizedBox(width: 8),
            Expanded(child: Text(m.name, style: const TextStyle(fontSize: 13))),
            if (m.id == effectiveModel) Icon(Icons.check, size: 16, color: colorScheme.primary),
          ],
        ),
      )).toList(),
      onSelected: (modelId) => modelProvider.setAgentModel(agentName, modelId),
    );
  }
}

class _FullSelector extends StatelessWidget {
  final String effectiveModel;
  final List<ModelInfo> models;
  final String agentName;
  final ModelProvider modelProvider;

  const _FullSelector({
    required this.effectiveModel,
    required this.models,
    required this.agentName,
    required this.modelProvider,
  });

  @override
  Widget build(BuildContext context) {
    return DropdownButton<String>(
      value: models.any((m) => m.id == effectiveModel) ? effectiveModel : null,
      isExpanded: true,
      hint: Text('Select model ($effectiveModel)'),
      items: models.map((m) => DropdownMenuItem(
        value: m.id,
        enabled: m.available,
        child: Row(
          children: [
            Text(ModelProvider.getProviderIcon(m.provider)),
            const SizedBox(width: 8),
            Text(m.name, style: const TextStyle(fontSize: 13)),
          ],
        ),
      )).toList(),
      onChanged: (val) {
        if (val != null) modelProvider.setAgentModel(agentName, val);
      },
    );
  }
}

String _shortModelName(String modelId) {
  if (modelId.contains('claude')) return 'Claude';
  if (modelId.contains('gpt')) return 'GPT-4o';
  if (modelId.startsWith('ollama:')) return 'Ollama';
  if (modelId == 'copilot') return 'Copilot';
  return modelId.length > 12 ? '${modelId.substring(0, 12)}…' : modelId;
}

String _resolveProvider(String modelId) {
  if (modelId.startsWith('ollama:')) return 'ollama';
  if (modelId == 'copilot') return 'copilot';
  if (modelId.contains('claude') || modelId.contains('anthropic')) return 'claude';
  if (modelId.contains('gpt') || modelId.contains('openai')) return 'openai';
  return 'claude';
}
