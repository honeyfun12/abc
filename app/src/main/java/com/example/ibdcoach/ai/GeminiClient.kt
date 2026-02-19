package com.example.ibdcoach.ai

import com.squareup.moshi.JsonClass
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.Query

interface GeminiApi {
    @POST("v1beta/models/gemini-1.5-flash:generateContent")
    suspend fun generate(
        @Query("key") apiKey: String,
        @Body request: GenerateRequest
    ): GenerateResponse
}

object GeminiClient {
    fun create(): GeminiApi {
        return Retrofit.Builder()
            .baseUrl("https://generativelanguage.googleapis.com/")
            .addConverterFactory(MoshiConverterFactory.create())
            .build()
            .create(GeminiApi::class.java)
    }
}

@JsonClass(generateAdapter = true)
data class GenerateRequest(val contents: List<Content>)

@JsonClass(generateAdapter = true)
data class Content(val parts: List<Part>)

@JsonClass(generateAdapter = true)
data class Part(val text: String)

@JsonClass(generateAdapter = true)
data class GenerateResponse(val candidates: List<Candidate>? = null)

@JsonClass(generateAdapter = true)
data class Candidate(val content: Content? = null)
