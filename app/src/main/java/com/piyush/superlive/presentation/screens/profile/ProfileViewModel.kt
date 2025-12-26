package com.piyush.superlive.presentation.screens.profile

import androidx.compose.runtime.State
import androidx.compose.runtime.mutableStateOf
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.piyush.superlive.common.Resource
import com.piyush.superlive.domain.usecase.GetProfileUseCase
import com.piyush.superlive.domain.usecase.UpdateProfileUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch

@HiltViewModel
class ProfileViewModel
@Inject
constructor(
        private val getProfileUseCase: GetProfileUseCase,
        private val updateProfileUseCase: UpdateProfileUseCase,
        savedStateHandle: SavedStateHandle
) : ViewModel() {

    private val _state = mutableStateOf(ProfileState())
    val state: State<ProfileState> = _state

    private val _eventFlow = MutableSharedFlow<UiEvent>()
    val eventFlow = _eventFlow.asSharedFlow()

    private val token: String? = savedStateHandle.get<String>("token")

    init {
        token?.let { getProfile(it) }
    }

    fun onEvent(event: ProfileEvent) {
        when (event) {
            is ProfileEvent.UpdateProfile -> {
                token?.let { updateProfile(it, event.name) }
            }
            is ProfileEvent.Refresh -> {
                token?.let { getProfile(it) }
            }
        }
    }

    private fun getProfile(token: String) {
        viewModelScope.launch {
            _state.value = state.value.copy(isLoading = true)
            when (val result = getProfileUseCase(token)) {
                is Resource.Success -> {
                    _state.value = state.value.copy(isLoading = false, profile = result.data?.data)
                }
                is Resource.Error -> {
                    _state.value =
                            state.value.copy(isLoading = false, error = result.message ?: "Error")
                    _eventFlow.emit(UiEvent.ShowSnackbar(result.message ?: "Error"))
                }
                is Resource.Loading -> {
                    _state.value = state.value.copy(isLoading = true)
                }
            }
        }
    }

    private fun updateProfile(token: String, name: String) {
        viewModelScope.launch {
            _state.value = state.value.copy(isLoading = true)
            when (val result = updateProfileUseCase(token, name)) {
                is Resource.Success -> {
                    _state.value = state.value.copy(isLoading = false, profile = result.data?.data)
                    _eventFlow.emit(UiEvent.ShowSnackbar("Profile Updated!"))
                }
                is Resource.Error -> {
                    _state.value =
                            state.value.copy(isLoading = false, error = result.message ?: "Error")
                    _eventFlow.emit(UiEvent.ShowSnackbar(result.message ?: "Error"))
                }
                is Resource.Loading -> {
                    _state.value = state.value.copy(isLoading = true)
                }
            }
        }
    }

    sealed class UiEvent {
        data class ShowSnackbar(val message: String) : UiEvent()
    }
}
