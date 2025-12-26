package com.piyush.superlive.domain.repository

import com.piyush.superlive.common.Resource
import com.piyush.superlive.domain.model.ProfileResponse

interface ProfileRepository {
    suspend fun getProfile(token: String): Resource<ProfileResponse>
    suspend fun updateProfile(token: String, name: String?): Resource<ProfileResponse>
}
