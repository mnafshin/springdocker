package io.github.mnafshin.springdocker.maven;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;

import org.junit.jupiter.api.Test;

class VerifyMojoTest {

    @Test
    void normalizeStripsAndUnifiesNewlines() {
        assertEquals("a\nb", VerifyMojo.normalize("a\r\nb\n"));
        assertNotEquals("a\nb", VerifyMojo.normalize("a\nb\nc"));
    }
}
