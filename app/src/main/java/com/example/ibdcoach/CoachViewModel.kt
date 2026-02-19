package com.example.ibdcoach

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.ibdcoach.ai.Content
import com.example.ibdcoach.ai.GenerateRequest
import com.example.ibdcoach.ai.GeminiClient
import com.example.ibdcoach.ai.Part
import com.example.ibdcoach.data.DailyPerformance
import com.example.ibdcoach.data.Difficulty
import com.example.ibdcoach.data.QuestionBank
import com.example.ibdcoach.data.QuestionConfig
import com.example.ibdcoach.data.SessionType
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlin.random.Random

data class CoachUiState(
    val selectedSession: SessionType = SessionType.SESSION1,
    val question: String = "시작 버튼을 누르면 질문이 나옵니다.",
    val transcript: String = "",
    val feedback: String = "",
    val isLoading: Boolean = false,
    val config: QuestionConfig = QuestionConfig(),
    val performance: DailyPerformance = DailyPerformance()
)

class CoachViewModel : ViewModel() {
    private val geminiApi = GeminiClient.create()

    private val _uiState = MutableStateFlow(CoachUiState())
    val uiState: StateFlow<CoachUiState> = _uiState.asStateFlow()

    fun setSession(sessionType: SessionType) {
        _uiState.update { it.copy(selectedSession = sessionType) }
    }

    fun updateTranscript(text: String) {
        _uiState.update { it.copy(transcript = text) }
    }

    fun updateTargetMinutes(minutes: Int) {
        _uiState.update { it.copy(config = it.config.copy(targetMinutes = minutes.coerceIn(3, 7))) }
    }

    fun toggleEquityResearch(enabled: Boolean) {
        _uiState.update { it.copy(config = it.config.copy(includeEquityResearch = enabled)) }
    }

    fun togglePrivateEquity(enabled: Boolean) {
        _uiState.update { it.copy(config = it.config.copy(includePrivateEquity = enabled)) }
    }

    fun startSession() {
        val state = _uiState.value
        val difficulty = when {
            state.performance.consecutiveHighDays >= 2 -> Difficulty.HARD
            state.performance.consecutiveLowDays >= 2 -> Difficulty.EASY
            else -> Difficulty.NORMAL
        }
        val question = QuestionBank.pickQuestion(
            sessionType = state.selectedSession,
            config = state.config,
            difficulty = difficulty,
            seed = Random.nextInt(0, 10_000)
        )
        _uiState.update {
            it.copy(
                question = "지금은 세션 ${state.selectedSession.id} 입니다. 오늘의 질문입니다. 녹음 버튼을 누르고 바로 답하세요.\n\n$question\n\n제한시간(권장): ${state.config.targetMinutes}분\n\n끝.",
                feedback = ""
            )
        }
    }

    fun analyzeAnswer() {
        val state = _uiState.value
        if (state.transcript.isBlank()) return

        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true) }

            val apiKey = BuildConfig.GOOGLE_AI_API_KEY
            if (apiKey.isBlank()) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        feedback = "API 키가 비어 있습니다. gradle.properties에 GOOGLE_AI_API_KEY를 넣어주세요."
                    )
                }
                return@launch
            }

            val prompt = buildPrompt(state.question, state.transcript)
            runCatching {
                geminiApi.generate(
                    apiKey = apiKey,
                    request = GenerateRequest(contents = listOf(Content(parts = listOf(Part(prompt)))))
                )
            }.onSuccess { response ->
                val text = response.candidates
                    ?.firstOrNull()
                    ?.content
                    ?.parts
                    ?.firstOrNull()
                    ?.text
                    ?: "피드백 생성 실패: 응답이 비어 있습니다."
                _uiState.update { it.copy(isLoading = false, feedback = text) }
            }.onFailure { error ->
                _uiState.update {
                    it.copy(isLoading = false, feedback = "피드백 생성 실패: ${error.message}")
                }
            }
        }
    }

    private fun buildPrompt(question: String, transcript: String): String {
        return """
너는 백수 집중모드 인터뷰 코치다.
출력은 반드시 한국어 설명 + 영어 모범답안 1개를 포함해라.
질문은 영어로 유지하고, 피드백 포맷은 아래를 엄수한다.

[질문]
$question

[사용자 전사]
$transcript

[출력 포맷]
한 줄 결론(첫 줄)
채점: X/10. 투자자/면접관 기준으로 합격/불합격. 이유 1문장.

구조(Structure) /10
- 시작 20초 결론 여부
- 3단 구조(결론→근거 2~3개→리스크/다음스텝) 여부

내용(Content) /10
- 정의 정확성
- 핵심 드라이버/유닛이코노믹스/리스크
- 밸류에이션 연결(멀티플/DCF/FCF)

실수/레드플래그(Mistakes)
- 개념 오류/용어 혼동/숫자관계 오류
- 영어표현 자연스러움과 전문성

면접관이 좋아할 한 문장(One-liner)
- 외워서 말할 문장 1개 (영어)

리테이크 지시(Replay)
- "2분 버전으로 다시 답해. 반드시 다음 템플릿을 사용해라:"
- 템플릿: (a) 결론 1문장 (b) 근거 3개(각 1문장) (c) 리스크 1개 + 대응 1개 (d) 마무리 1문장

모범답안 (영어, 45~75초)
""".trimIndent()
    }
}
