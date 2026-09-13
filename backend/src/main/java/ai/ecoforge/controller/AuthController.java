package ai.ecoforge.controller;

import ai.ecoforge.dto.Dtos;
import ai.ecoforge.entity.AppUser;
import ai.ecoforge.exception.ValidationException;
import ai.ecoforge.repository.Repositories.UserRepository;
import ai.ecoforge.security.JwtService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final UserRepository users;
    private final PasswordEncoder encoder;
    private final JwtService jwt;

    public AuthController(UserRepository users, PasswordEncoder encoder, JwtService jwt) {
        this.users = users;
        this.encoder = encoder;
        this.jwt = jwt;
    }

    @PostMapping("/register")
    public ResponseEntity<Dtos.AuthResponse> register(@Valid @RequestBody Dtos.RegisterRequest req) {
        users.findByEmailIgnoreCase(req.email()).ifPresent(u -> {
            throw new ValidationException("An account already exists for that email address.");
        });
        AppUser user = new AppUser();
        user.setEmail(req.email().toLowerCase());
        user.setDisplayName(req.displayName());
        user.setPasswordHash(encoder.encode(req.password()));
        users.save(user);
        return ResponseEntity.ok(token(user));
    }

    @PostMapping("/login")
    public ResponseEntity<Dtos.AuthResponse> login(@Valid @RequestBody Dtos.LoginRequest req) {
        AppUser user = users.findByEmailIgnoreCase(req.email())
                .filter(u -> encoder.matches(req.password(), u.getPasswordHash()))
                .orElseThrow(() -> new ValidationException(
                        "That email address and password do not match an account."));
        return ResponseEntity.ok(token(user));
    }

    private Dtos.AuthResponse token(AppUser user) {
        return new Dtos.AuthResponse(
                jwt.issue(user.getEmail(), user.getRole(), user.getDisplayName()),
                user.getDisplayName(), user.getRole(), jwt.ttlSeconds());
    }
}
