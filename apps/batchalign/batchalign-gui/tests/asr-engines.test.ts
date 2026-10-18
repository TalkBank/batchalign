import { expect, test } from 'vitest';
import { availableAsr, asrLanguage, recommendedAsr, selectedAsr } from '../src/asrEngines';
import { buildRecipeKwargs } from '../src/desktop';

test('no engines appear until a language is entered', () => {
  for (const language of ['', ' ', 'e', 'engl', 'zzz', 'xyz', 'English', 'zh']) expect(recommendedAsr(language)).toEqual([]);
});
test('recommendations follow language and omit retired engines', () => {
  expect(recommendedAsr('eng')).toEqual(['RevAI', 'ChatWhisperBackend']);
  expect(recommendedAsr('yue').slice(0, 2)).toEqual(['AliyunAsrBackend', 'FunAsrBackend']);
  expect(recommendedAsr('zho')).toEqual(['RevAI', 'FunAudioBackend']);
  expect(recommendedAsr('spa')).toEqual(['RevAI', 'GoogleGenAIBackend', 'OpenAIWhisperBackend', 'Qwen3AsrBackend']);
  expect(selectedAsr('eng', 'WhisperBackend')).toBe('');
  expect(selectedAsr('eng', 'RevAI')).toBe('RevAI');
  expect(availableAsr('eng', ['WhisperBackend'])).toEqual(['RevAI']);
});

test('recommendations fall back to available cloud and local engines', () => {
  expect(recommendedAsr('yue', ['FunAudioBackend'])).toEqual(['RevAI', 'FunAsrBackend']);
  expect(recommendedAsr('eng', ['Qwen3AsrBackend'])).toEqual(['RevAI', 'Qwen3AsrBackend']);
  expect(recommendedAsr('zho', ['OpenAIWhisperBackend'])).toEqual(['RevAI', 'OpenAIWhisperBackend']);
  expect(recommendedAsr('eng', [])).toEqual(['RevAI']);
});
test('language-specific labels run the actual advertised models with valid arguments', () => {
  expect(buildRecipeKwargs('transcribe', { lang: 'zho', engine: 'FunAudioBackend' })).toMatchObject({
    asr_backend: { kind: 'FunAudioBackend', kwargs: { language: 'zho', model: 'funasr/paraformer-zh' } },
  });
  expect(buildRecipeKwargs('transcribe', { lang: 'yue', engine: 'FunAsrBackend' })).toMatchObject({
    asr_backend: { kind: 'FunAudioBackend', kwargs: { language: 'yue', model: 'FunAudioLLM/SenseVoiceSmall' } },
  });
  expect(buildRecipeKwargs('transcribe', { lang: 'yue', engine: 'AliyunAsrBackend' })).toMatchObject({
    asr_backend: { kind: 'AliyunAsrBackend', kwargs: {} },
  });
});

test('language validation preserves canonical codes and ASR requires explicit selection', () => {
  expect(asrLanguage(' ZHO ')).toBe('zho');
  expect(asrLanguage('cmn')).toBe('cmn');
  expect(asrLanguage('xyz')).toBe('');
  expect(selectedAsr('eng')).toBe('');
  expect(selectedAsr('eng', 'FunAudioBackend')).toBe('FunAudioBackend');
  expect(availableAsr('eng')).toContain('RevAI');
  expect(availableAsr('yue')).toContain('ChatWhisperBackend');
});
