package com.piyush.superlive.di

import com.piyush.superlive.common.Constants
import com.piyush.superlive.data.remote.SuperliveApi
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideOkHttpClient(): OkHttpClient {
        return OkHttpClient.Builder()
                .addInterceptor(
                        HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BODY }
                )
                .build()
    }

    @Provides
    @Singleton
    fun provideSuperliveApi(client: OkHttpClient): SuperliveApi {
        return Retrofit.Builder()
                .baseUrl(Constants.BASE_URL)
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(SuperliveApi::class.java)
    }

    @Provides
    @Singleton
    fun provideAuthRepository(
            api: SuperliveApi
    ): com.piyush.superlive.domain.repository.AuthRepository {
        return com.piyush.superlive.data.repository.AuthRepositoryImpl(api)
    }

    @Provides
    @Singleton
    fun provideProfileRepository(
            api: SuperliveApi
    ): com.piyush.superlive.domain.repository.ProfileRepository {
        return com.piyush.superlive.data.repository.ProfileRepositoryImpl(api)
    }
}
