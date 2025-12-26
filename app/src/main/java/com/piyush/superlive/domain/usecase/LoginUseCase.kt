package com.piyush.superlive.domain.usecase

import com.piyush.superlive.common.Resource
import com.piyush.superlive.domain.model.LoginResponse
import com.piyush.superlive.domain.repository.AuthRepository
import javax.inject.Inject

class LoginUseCase @Inject constructor(private val repository: AuthRepository) {
    suspend operator fun invoke(email: String, password: String): Resource<LoginResponse> {
        if (email.isBlank() || password.isBlank()) {
            return Resource.Error("Email and password cannot be empty")
        }
        return repository.login(email, password)
    }
}
