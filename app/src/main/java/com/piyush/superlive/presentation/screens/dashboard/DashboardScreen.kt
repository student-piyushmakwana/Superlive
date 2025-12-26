package com.piyush.superlive.presentation.screens.dashboard

import androidx.compose.foundation.layout.*
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun DashboardScreen(token: String, onNavigateToProfile: (String) -> Unit) {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text("Welcome to Dashboard!")
            Spacer(modifier = Modifier.height(16.dp))
            Button(onClick = { onNavigateToProfile(token) }) { Text("Go to Profile") }
        }
    }
}
