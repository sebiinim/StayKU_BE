package com.example.stayku

import android.content.Intent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.platform.LocalContext
import android.app.Activity

// 다른 화면으로 이동할 때 필요한 Composable 함수들
import com.example.stayku.ProfileScreen
import com.example.stayku.ChatActivity
import com.example.stayku.TeamScreen
import com.example.stayku.MatchRecommendScreen
import com.example.stayku.LoginScreen

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(userId: String, onLogout: () -> Unit) {
    var currentPage by remember { mutableStateOf("home") }

    when (currentPage) {
        "home" -> {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("환영합니다, $userId 님!")

                val context = LocalContext.current
                Button(onClick = {
                    val intent = Intent(context, ProfileActivity::class.java)
                    intent.putExtra("userId", userId)
                    context.startActivity(intent)
                }) {
                    Text("내 프로필 등록/수정")
                }

                Button(onClick = {
                    val intent = Intent(context, ChatActivity::class.java)
                    intent.putExtra("userId", userId)
                    context.startActivity(intent)
                }) {
                    Text("1:1 채팅하기")
                }

                Button(onClick = { currentPage = "team" }) {
                    Text("룸메이트 팀 구성")
                }

                Button(onClick = { currentPage = "match" }) {
                    Text("추천 매칭 보기")
                }

                val activity = context as? Activity

                Button(
                    onClick = {
                        onLogout()
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 32.dp)
                ) {
                    Text("로그아웃")
                }
            }
        }
        "profile" -> ProfileScreen(userId = userId)
        "chat" -> ChatScreen(userId = userId)
        "team" -> TeamScreen(userId = userId)
        "match" -> MatchRecommendScreen(userId = userId)
    }
}
