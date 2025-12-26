package com.piyush.superlive.presentation.screens.profile

import android.widget.Toast
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import kotlinx.coroutines.flow.collectLatest

@Composable
fun ProfileScreen(viewModel: ProfileViewModel = hiltViewModel()) {
    val state = viewModel.state.value
    val context = LocalContext.current
    var name by remember { mutableStateOf("") }

    LaunchedEffect(key1 = true) {
        viewModel.eventFlow.collectLatest { event ->
            when (event) {
                is ProfileViewModel.UiEvent.ShowSnackbar -> {
                    Toast.makeText(context, event.message, Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    // Update local state when profile loads
    LaunchedEffect(state.profile) { state.profile?.let { name = it.name } }

    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        if (state.isLoading) {
            CircularProgressIndicator()
        } else {
            Column(
                    modifier = Modifier.fillMaxSize().padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(text = "Profile", style = MaterialTheme.typography.headlineMedium)

                Spacer(modifier = Modifier.height(32.dp))

                state.profile?.let { profile ->
                    Text(text = "Email: ${profile.email}")
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(text = "Coins: ${profile.coins}")

                    Spacer(modifier = Modifier.height(16.dp))

                    OutlinedTextField(
                            value = name,
                            onValueChange = { name = it },
                            label = { Text("Name") },
                            modifier = Modifier.fillMaxWidth()
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    Button(
                            onClick = { viewModel.onEvent(ProfileEvent.UpdateProfile(name)) },
                            modifier = Modifier.fillMaxWidth()
                    ) { Text("Update Profile") }
                }
                        ?: run {
                            Text(text = "No profile data loaded.")
                            Button(onClick = { viewModel.onEvent(ProfileEvent.Refresh) }) {
                                Text("Retry")
                            }
                        }
            }
        }
    }
}
