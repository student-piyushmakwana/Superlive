package com.piyush.superlive.data.repository

import com.piyush.superlive.common.Resource
import com.piyush.superlive.data.remote.SuperliveApi
import com.piyush.superlive.domain.model.ProfileRequest
import com.piyush.superlive.domain.model.ProfileResponse
import com.piyush.superlive.domain.model.UpdateProfileRequest
import com.piyush.superlive.domain.repository.ProfileRepository
import javax.inject.Inject

class ProfileRepositoryImpl @Inject constructor(private val api: SuperliveApi) : ProfileRepository {

    override suspend fun getProfile(token: String): Resource<ProfileResponse> {
        return try {
            val response = api.getProfile(ProfileRequest(token))
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else {
                Resource.Error(response.message() ?: "Unknown error")
            }
        } catch (e: Exception) {
            Resource.Error("Couldn't reach server. Check your internet connection.")
        }
    }

    override suspend fun updateProfile(token: String, name: String?): Resource<ProfileResponse> {
        return try {
            val response = api.updateProfile(UpdateProfileRequest(token, name))
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else {
                Resource.Error(response.message() ?: "Unknown error")
            }
        } catch (e: Exception) {
            Resource.Error("Couldn't reach server. Check your internet connection.")
        }
    }
}
