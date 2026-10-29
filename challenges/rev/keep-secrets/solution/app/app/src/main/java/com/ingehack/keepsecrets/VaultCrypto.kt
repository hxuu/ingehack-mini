package com.ingehack.keepsecrets

import android.util.Base64
import java.security.MessageDigest
import javax.crypto.Cipher
import javax.crypto.spec.SecretKeySpec

object VaultCrypto {
    private const val FIRST = "All hail"
    private const val SECOND = "Lelouch"
    private val PASSPHRASE = "$FIRST $SECOND"
    private val KEY = MessageDigest.getInstance("SHA-256")
        .digest(PASSPHRASE.toByteArray(Charsets.UTF_8))

    fun seal(plaintext: String): String {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, SecretKeySpec(KEY, "AES"))
        val iv = cipher.iv
        val ciphertext = cipher.doFinal(plaintext.toByteArray(Charsets.UTF_8))
        return Base64.encodeToString(iv + ciphertext, Base64.NO_WRAP)
    }
}
