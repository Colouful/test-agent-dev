<!-- frontend/src/pages/QuestionDetailPage.vue -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { defineComponent, h, ref as vref } from 'vue'
import { useRoute } from 'vue-router'
import { IS_MOCK, mockQuestions } from '@/api/mock'
import { questionsApi } from '@/api/endpoints/questions'
import type { Question } from '@/types'

const PracticeAnswerToggle = defineComponent({
  props: { answer: String, explanation: String },
  setup(props) {
    const show = vref(false)
    return () => h('div', [
      !show.value
        ? h('button', {
            onClick: () => { show.value = true },
            class: 'text-xs text-primary-500 border border-primary-300 rounded-lg px-3 py-1.5 hover:bg-primary-50 transition-colors',
          }, '查看答案')
        : h('div', { class: 'space-y-1' }, [
            h('p', { class: 'text-sm font-medium text-green-700' }, `答案：${props.answer}`),
            h('p', { class: 'text-xs text-gray-500 leading-relaxed mt-1' }, props.explanation),
          ]),
    ])
  },
})

const route = useRoute()
const question = ref<Question | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    const id = route.params.id as string
    if (IS_MOCK) {
      const resp = await mockQuestions.get(id)
      if (resp.error) {
        error.value = resp.error.message || '题目不存在'
      } else {
        question.value = resp.data
      }
    } else {
      const resp = await questionsApi.get(id)
      question.value = resp.data.data
    }
  } catch {
    error.value = '加载失败，请返回重试'
  } finally {
    loading.value = false
  }
})

const TYPE_LABELS: Record<string, string> = {
  multiple_choice: '选择题',
  fill: '填空题',
  short_answer: '简答题',
  calculation: '计算题',
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 pb-20">
    <!-- 顶部标题栏 -->
    <header class="bg-white border-b sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3 flex items-center gap-3">
        <button @click="$router.back()" class="text-gray-400 hover:text-gray-600 transition-colors">
          ←
        </button>
        <h2 class="font-semibold text-gray-900">错题详情</h2>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-4 space-y-4">
      <!-- 加载中 -->
      <div v-if="loading" class="space-y-3">
        <div class="h-6 bg-gray-200 rounded animate-pulse w-1/3"></div>
        <div class="h-32 bg-gray-200 rounded animate-pulse"></div>
        <div class="h-20 bg-gray-200 rounded animate-pulse"></div>
      </div>

      <!-- 加载失败 -->
      <div v-else-if="error" class="text-center py-16 text-gray-400">
        <div class="text-4xl mb-3">⚠️</div>
        <p>{{ error }}</p>
      </div>

      <!-- 内容 -->
      <template v-else-if="question">
        <!-- 标签行 -->
        <div class="flex flex-wrap gap-2">
          <span v-if="question.subject"
            class="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium">
            {{ question.subject }}
          </span>
          <span v-if="question.question_type && TYPE_LABELS[question.question_type]"
            class="text-xs px-2 py-0.5 rounded-full bg-purple-50 text-purple-600 font-medium">
            {{ TYPE_LABELS[question.question_type] }}
          </span>
          <span :class="[
            'text-xs px-2 py-0.5 rounded-full font-medium',
            question.status === 'confirmed'
              ? 'bg-green-50 text-green-600'
              : 'bg-yellow-50 text-yellow-600'
          ]">
            {{ question.status === 'confirmed' ? '已确认' : '待确认' }}
          </span>
        </div>

        <!-- 图片 -->
        <div v-if="question.image_url" class="bg-white rounded-2xl overflow-hidden shadow-sm">
          <img :src="question.image_url" alt="题目图片"
            class="w-full object-contain bg-gray-50 max-h-72" loading="lazy">
        </div>

        <!-- 题目内容 -->
        <div class="bg-white rounded-2xl shadow-sm p-5">
          <p class="text-xs text-gray-400 mb-2">题目内容</p>
          <p class="font-serif text-gray-800 text-base leading-relaxed whitespace-pre-wrap">
            {{ question.content }}
          </p>
        </div>

        <!-- 答案区 -->
        <div class="bg-white rounded-2xl shadow-sm p-5 space-y-4">
          <div>
            <p class="text-xs text-gray-400 mb-1.5">正确答案</p>
            <p class="text-green-700 font-medium leading-relaxed">{{ question.correct_answer }}</p>
          </div>
          <div v-if="question.wrong_answer" class="border-t border-gray-100 pt-4">
            <p class="text-xs text-gray-400 mb-1.5">我的错误</p>
            <p class="text-red-500 leading-relaxed">{{ question.wrong_answer }}</p>
          </div>
          <div v-if="question.note" class="border-t border-gray-100 pt-4">
            <p class="text-xs text-gray-400 mb-1.5">笔记</p>
            <p class="text-gray-600 italic leading-relaxed">{{ question.note }}</p>
          </div>
        </div>

        <!-- AI 解析卡片 -->
        <div v-if="question.analysis" class="bg-white rounded-2xl shadow-sm p-5 space-y-5">
          <h3 class="font-semibold text-gray-800 flex items-center gap-2">
            <span>💡</span> AI 解析
          </h3>

          <!-- 新格式：解题思路 -->
          <div v-if="question.analysis.solution_summary" class="bg-gray-50 rounded-lg p-3">
            <p class="text-xs text-gray-400 mb-1">解题思路</p>
            <p class="text-sm text-gray-700 leading-relaxed">{{ question.analysis.solution_summary }}</p>
          </div>
          <!-- 旧格式降级 -->
          <div v-else-if="question.analysis.explanation" class="bg-gray-50 rounded-lg p-3">
            <p class="text-xs text-gray-400 mb-1">答案解析</p>
            <p class="text-sm text-gray-700 leading-relaxed">{{ question.analysis.explanation }}</p>
          </div>

          <!-- 分步解析 -->
          <div v-if="question.analysis.solution_steps && question.analysis.solution_steps.length">
            <p class="text-xs text-gray-400 mb-2">分步解析</p>
            <div class="space-y-2">
              <div
                v-for="step in question.analysis.solution_steps"
                :key="step.step"
                class="flex gap-3 items-start"
              >
                <span class="shrink-0 w-6 h-6 rounded-full bg-primary-100 text-primary-600
                             text-xs font-bold flex items-center justify-center mt-0.5">
                  {{ step.step }}
                </span>
                <div>
                  <p class="text-sm font-medium text-gray-700">{{ step.title }}</p>
                  <p class="text-sm text-gray-500 leading-relaxed mt-0.5">{{ step.content }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 知识点 -->
          <div v-if="question.analysis.knowledge_points">
            <p class="text-xs text-gray-400 mb-1.5">涉及知识点</p>
            <!-- 新格式：分层知识点 -->
            <template v-if="!Array.isArray(question.analysis.knowledge_points)">
              <div class="flex flex-wrap gap-1.5">
                <span
                  v-for="kp in (question.analysis.knowledge_points as any).core"
                  :key="'core-'+kp"
                  class="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full"
                >{{ kp }}</span>
                <span
                  v-for="kp in (question.analysis.knowledge_points as any).prerequisite"
                  :key="'pre-'+kp"
                  class="text-xs px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full"
                >前置: {{ kp }}</span>
                <span
                  v-for="kp in (question.analysis.knowledge_points as any).related"
                  :key="'rel-'+kp"
                  class="text-xs px-2 py-0.5 bg-green-50 text-green-600 rounded-full"
                >关联: {{ kp }}</span>
              </div>
            </template>
            <!-- 旧格式降级：list[str] -->
            <template v-else>
              <div class="flex flex-wrap gap-1.5">
                <span
                  v-for="kp in (question.analysis.knowledge_points as string[])"
                  :key="kp"
                  class="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full"
                >{{ kp }}</span>
              </div>
            </template>
          </div>

          <!-- 考查要点 -->
          <div v-if="question.analysis.key_examination">
            <p class="text-xs text-gray-400 mb-1">考查要点</p>
            <p class="text-sm text-amber-700 leading-relaxed">{{ question.analysis.key_examination }}</p>
          </div>

          <!-- 错因分析（新格式） -->
          <div v-if="question.analysis.error_analysis">
            <p class="text-xs text-gray-400 mb-2">错因分析</p>
            <div class="space-y-2">
              <span class="inline-block text-xs px-2 py-0.5 bg-red-50 text-red-600 rounded-full font-medium">
                {{ question.analysis.error_analysis.type }}
              </span>
              <p class="text-sm text-red-600 leading-relaxed">{{ question.analysis.error_analysis.reason }}</p>
              <div v-if="question.analysis.error_analysis.improvement.length" class="space-y-1 pt-1">
                <p class="text-xs text-gray-400">改进建议</p>
                <p
                  v-for="(tip, i) in question.analysis.error_analysis.improvement"
                  :key="i"
                  class="text-sm text-green-700 leading-relaxed flex gap-1.5"
                >
                  <span class="shrink-0">✓</span>{{ tip }}
                </p>
              </div>
            </div>
          </div>
          <!-- 旧格式降级：error_reason -->
          <div v-else-if="question.analysis.error_reason">
            <p class="text-xs text-gray-400 mb-1">为什么会出错</p>
            <p class="text-sm text-red-600 leading-relaxed">{{ question.analysis.error_reason }}</p>
          </div>

          <!-- 常见错误 -->
          <div v-if="question.analysis.common_mistakes && question.analysis.common_mistakes.length">
            <p class="text-xs text-gray-400 mb-1.5">常见错误</p>
            <div class="space-y-1">
              <div
                v-for="(m, i) in question.analysis.common_mistakes"
                :key="i"
                class="text-sm text-yellow-700 bg-yellow-50 border-l-2 border-yellow-400 px-3 py-1.5 rounded-r-lg"
              >
                ⚠️ {{ m }}
              </div>
            </div>
          </div>

          <!-- 举一反三 -->
          <div v-if="question.analysis.practice_questions && question.analysis.practice_questions.length">
            <p class="text-xs text-gray-400 mb-2">📝 举一反三</p>
            <div
              v-for="(pq, i) in question.analysis.practice_questions"
              :key="i"
              class="border border-gray-200 rounded-xl p-4 space-y-3"
            >
              <p class="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">{{ pq.content }}</p>
              <PracticeAnswerToggle :answer="pq.answer" :explanation="pq.explanation" />
            </div>
          </div>
        </div>

        <!-- 统计信息 -->
        <div class="bg-white rounded-2xl shadow-sm p-5">
          <p class="text-xs text-gray-400 mb-3">复习记录</p>
          <div class="grid grid-cols-3 gap-4 text-center">
            <div>
              <p class="text-xl font-bold text-gray-800">{{ question.review_count }}</p>
              <p class="text-xs text-gray-400 mt-0.5">复习次数</p>
            </div>
            <div>
              <p class="text-xl font-bold text-gray-800">{{ question.interval_days }}</p>
              <p class="text-xs text-gray-400 mt-0.5">复习间隔(天)</p>
            </div>
            <div>
              <p class="text-xl font-bold text-gray-800">{{ question.ease_factor.toFixed(1) }}</p>
              <p class="text-xs text-gray-400 mt-0.5">难度系数</p>
            </div>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>
