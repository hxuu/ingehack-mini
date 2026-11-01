package com.ingehack.keepsecrets

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

@Composable
fun KeepSecretsApp() {
    var draft by rememberSaveable { androidx.compose.runtime.mutableStateOf("") }
    val entries = remember {
        mutableStateListOf<VaultEntry>().apply { addAll(SecretData.BAKED_SECRETS) }
    }
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Ink),
    ) {
        Hero(entries.size)

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .navigationBarsPadding()
                .imePadding()
                .padding(horizontal = 20.dp),
        ) {
            Spacer(Modifier.height(16.dp))
            Sealer(
                draft = draft,
                onDraftChange = { draft = it },
                onSeal = {
                    if (draft.isNotBlank()) {
                        entries.add(0, VaultEntry("Unlabeled", VaultCrypto.seal(draft)))
                        draft = ""
                        scope.launch { listState.animateScrollToItem(0) }
                    }
                },
            )
            Spacer(Modifier.height(16.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "SEALED ENTRIES",
                    style = MaterialTheme.typography.labelLarge,
                    color = Gold,
                )
                Spacer(Modifier.weight(1f))
                Text(
                    text = entries.size.toString().padStart(2, '0'),
                    style = MaterialTheme.typography.labelMedium,
                    color = Muted,
                )
            }
            Spacer(Modifier.height(10.dp))
            LazyColumn(
                state = listState,
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(10.dp),
                contentPadding = PaddingValues(bottom = 24.dp),
            ) {
                items(items = entries, key = { it.ciphertext }) { entry ->
                    VaultCard(entry)
                }
            }
        }
    }
}

@Composable
private fun Hero(count: Int) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(330.dp),
    ) {
        Image(
            painter = painterResource(R.drawable.keepsecrets_bg),
            contentDescription = null,
            contentScale = ContentScale.Crop,
            alignment = Alignment.Center,
            modifier = Modifier.fillMaxSize(),
        )
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        0f to Color(0xE60B0612),
                        0.24f to Color(0x990B0612),
                        0.55f to Color(0x400B0612),
                        0.82f to Color(0xB30B0612),
                        1f to Ink,
                    ),
                ),
        )
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .padding(horizontal = 20.dp),
        ) {
            Spacer(Modifier.height(18.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "BLACK KNIGHTS  //  PRIVATE LEDGER",
                    style = MaterialTheme.typography.labelMedium,
                    color = Gold,
                )
                Spacer(Modifier.weight(1f))
                Text(
                    text = "${count.toString().padStart(2, '0')} SEALED",
                    style = MaterialTheme.typography.labelMedium,
                    color = Violet,
                )
            }
            Spacer(Modifier.height(14.dp))
            Text(
                text = buildAnnotatedString {
                    append("Keep ")
                    withStyle(SpanStyle(color = Gold)) { append("Secrets") }
                },
                style = MaterialTheme.typography.displayLarge,
                color = Parchment,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                text = "A private ledger for the Black Knights. Every entry is sealed with a command only Zero knows.",
                style = MaterialTheme.typography.bodyMedium,
                color = Muted,
            )
        }
    }
}

@Composable
private fun Sealer(
    draft: String,
    onDraftChange: (String) -> Unit,
    onSeal: () -> Unit,
) {
    Surface(
        color = Color(0xD9120A1C),
        shape = RoundedCornerShape(2.dp),
        border = BorderStroke(1.dp, Gold.copy(alpha = 0.18f)),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = "NEW ENTRY",
                    style = MaterialTheme.typography.labelLarge,
                    color = Gold,
                )
                Spacer(Modifier.weight(1f))
                Text(
                    text = "LOCAL ONLY",
                    style = MaterialTheme.typography.labelMedium,
                    color = Muted,
                )
            }
            Spacer(Modifier.height(10.dp))
            OutlinedTextField(
                value = draft,
                onValueChange = onDraftChange,
                modifier = Modifier.fillMaxWidth(),
                placeholder = {
                    Text(
                        text = "A secret you would not say aloud.",
                        color = Muted.copy(alpha = 0.7f),
                    )
                },
                minLines = 2,
                maxLines = 3,
                shape = RoundedCornerShape(2.dp),
                textStyle = MaterialTheme.typography.bodyLarge,
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Gold,
                    unfocusedBorderColor = Outline,
                    focusedContainerColor = Color(0x66120A1C),
                    unfocusedContainerColor = Color(0x33120A1C),
                    cursorColor = Gold,
                    focusedTextColor = Parchment,
                    unfocusedTextColor = Parchment,
                ),
            )
            Spacer(Modifier.height(10.dp))
            Button(
                onClick = onSeal,
                enabled = draft.isNotBlank(),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp),
                shape = RoundedCornerShape(2.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Gold,
                    contentColor = Ink,
                    disabledContainerColor = Gold.copy(alpha = 0.18f),
                    disabledContentColor = Muted.copy(alpha = 0.6f),
                ),
            ) {
                Text(
                    text = "SEAL ENTRY",
                    style = MaterialTheme.typography.labelLarge,
                )
            }
        }
    }
}

@Composable
private fun VaultCard(entry: VaultEntry) {
    Surface(
        color = Color(0xD90F0818),
        shape = RoundedCornerShape(2.dp),
        border = BorderStroke(1.dp, Gold.copy(alpha = 0.14f)),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(4.dp)
                        .background(Gold, CircleShape),
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    text = entry.title.uppercase(),
                    style = MaterialTheme.typography.labelLarge,
                    color = Gold,
                )
                Spacer(Modifier.weight(1f))
                Text(
                    text = "SEALED",
                    style = MaterialTheme.typography.labelMedium,
                    color = Violet,
                )
            }
            Spacer(Modifier.height(10.dp))
            SelectionContainer {
                Text(
                    text = entry.ciphertext,
                    color = Color(0xFFD6C6E4),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 11.sp,
                    lineHeight = 17.sp,
                )
            }
        }
    }
}
