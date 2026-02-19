package com.example.ibdcoach

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.ibdcoach.data.SessionType
import com.example.ibdcoach.ui.theme.IBDVoiceCoachTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            IBDVoiceCoachTheme {
                CoachScreen()
            }
        }
    }
}

@Composable
fun CoachScreen(vm: CoachViewModel = viewModel()) {
    val state by vm.uiState.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("데일리 IBD + 테크 + 밸류에이션 음성 인터뷰 코치", style = MaterialTheme.typography.titleMedium)

        SessionType.entries.forEach { session ->
            Button(
                onClick = { vm.setSession(session) },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("세션 ${session.id}: ${session.label} (${session.defaultTime})")
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("질문 옵션", style = MaterialTheme.typography.titleSmall)
                Text("목표 답변 시간: ${state.config.targetMinutes}분")
                Slider(
                    value = state.config.targetMinutes.toFloat(),
                    onValueChange = { vm.updateTargetMinutes(it.toInt()) },
                    valueRange = 3f..7f,
                    steps = 3
                )
                Row {
                    Checkbox(
                        checked = state.config.includeEquityResearch,
                        onCheckedChange = vm::toggleEquityResearch
                    )
                    Text("Equity Research 질문 포함")
                }
                Row {
                    Checkbox(
                        checked = state.config.includePrivateEquity,
                        onCheckedChange = vm::togglePrivateEquity
                    )
                    Text("PE 질문 포함")
                }
            }
        }

        Button(onClick = vm::startSession, modifier = Modifier.fillMaxWidth()) {
            Text("시작")
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Text(state.question, modifier = Modifier.padding(12.dp))
        }

        OutlinedTextField(
            value = state.transcript,
            onValueChange = vm::updateTranscript,
            label = { Text("녹음 전사 텍스트 붙여넣기") },
            modifier = Modifier.fillMaxWidth().height(180.dp)
        )

        Button(onClick = vm::analyzeAnswer, modifier = Modifier.fillMaxWidth()) {
            Text("채점 + 피드백 + 리테이크 요청")
        }

        if (state.isLoading) {
            CircularProgressIndicator()
        }

        if (state.feedback.isNotBlank()) {
            Card(modifier = Modifier.fillMaxWidth()) {
                Text(state.feedback, modifier = Modifier.padding(12.dp))
            }
        }

        Spacer(modifier = Modifier.height(20.dp))
    }
}
