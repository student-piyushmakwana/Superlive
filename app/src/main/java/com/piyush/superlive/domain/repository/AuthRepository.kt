package com.piyush.superlive.domain.repository

import com.piyush.superlive.common.Resource
import com.piyush.superlive.domain.model.LoginResponse

interface AuthRepository {
    suspend fun login(email: String, password: String): Resource<LoginResponse>
}
