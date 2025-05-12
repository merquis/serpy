function Push-Changes {
    Write-Host "🚀 Subiendo cambios a GitHub..." -ForegroundColor Cyan
    git add .
    if ($?) {
        git commit -m "Actualización automática de código"
        if ($?) {
            git push
            if ($?) {
                Write-Host "✅ Cambios subidos exitosamente" -ForegroundColor Green
            } else {
                Write-Host "❌ Error al hacer push" -ForegroundColor Red
            }
        } else {
            Write-Host "❌ Error al hacer commit" -ForegroundColor Red
        }
    } else {
        Write-Host "❌ Error al agregar archivos" -ForegroundColor Red
    }
}

Set-Alias -Name push -Value Push-Changes 