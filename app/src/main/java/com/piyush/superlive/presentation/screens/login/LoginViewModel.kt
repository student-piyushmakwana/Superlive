package com.piyush.superlive.presentation.screens.login

import androidx.compose.runtime.State
import androidx.compose.runtime.mutableStateOf
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.piyush.superlive.common.Resource
import com.piyush.superlive.domain.usecase.LoginUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch

@HiltViewModel
class LoginViewModel @Inject constructor(private val loginUseCase: LoginUseCase) : ViewModel() {

    private val _state = mutableStateOf(LoginState())
    val state: State<LoginState> = _state

    private val _eventFlow = MutableSharedFlow<UiEvent>()
    val eventFlow = _eventFlow.asSharedFlow()

    fun onEvent(event: LoginEvent) {
        when (event) {
            is LoginEvent.Result -> {
                // Not used in this direction usually
            }
            is LoginEvent.Login -> {
                login(event.email, event.password)
            }
        }
    }

    private fun login(email: String, password: String) {
        viewModelScope.launch {
            _state.value = state.value.copy(isLoading = true)

            when (val result = loginUseCase(email, password)) {
                is Resource.Success -> {
                    _state.value = state.value.copy(isLoading = false, token = result.data?.token)
                    _eventFlow.emit(UiEvent.NavigateToDashboard)
                }
                is Resource.Error -> {
                    _state.value =
                            state.value.copy(
                                    isLoading = false,
                                    error = result.message ?: "Unknown error"
                            )
                    _eventFlow.emit(UiEvent.ShowSnackbar(result.message ?: "Unknown error"))
                }
                is Resource.Loading -> {
                    _state.value = state.value.copy(isLoading = true)
                }
            }
        }
    }

    sealed class UiEvent {
        data class ShowSnackbar(val message: String) : UiEvent()
        object NavigateToDashboard : UiEvent()
    }
}
