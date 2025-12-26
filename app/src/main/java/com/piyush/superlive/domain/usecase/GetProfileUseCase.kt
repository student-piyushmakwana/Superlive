package com.piyush.superlive.domain.usecase

import com.piyush.superlive.common.Resource
import com.piyush.superlive.domain.model.ProfileResponse
import com.piyush.superlive.domain.repository.ProfileRepository
import javax.inject.Inject

class GetProfileUseCase @Inject constructor(private val repository: ProfileRepository) {
    suspend operator fun invoke(token: String): Resource<ProfileResponse> {
        return repository.getProfile(token)
    }
}
