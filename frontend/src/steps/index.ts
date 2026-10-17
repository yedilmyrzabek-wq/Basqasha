import type { ComponentType } from 'react'
import type { StepKey } from '@/api/client'
import FactsStep from './FactsStep'
import IdeaStep from './IdeaStep'
import ImagesStep from './ImagesStep'
import MetadataStep from './MetadataStep'
import PreviewStep from './PreviewStep'
import RecommendationsStep from './RecommendationsStep'
import RenderStep from './RenderStep'
import ScriptStep from './ScriptStep'
import SourceStep from './SourceStep'
import StoryboardStep from './StoryboardStep'
import type { StepViewProps } from './types'
import VoiceStep from './VoiceStep'

export const STEP_VIEWS: Record<StepKey, ComponentType<StepViewProps>> = {
  source: SourceStep,
  idea: IdeaStep,
  facts: FactsStep,
  script: ScriptStep,
  voice: VoiceStep,
  storyboard: StoryboardStep,
  images: ImagesStep,
  preview: PreviewStep,
  render: RenderStep,
  metadata: MetadataStep,
  recommendations: RecommendationsStep,
}
