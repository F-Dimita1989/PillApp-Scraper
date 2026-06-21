using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace PillApp.Api.DrugImages;

/// <summary>
/// Endpoint esposto a React Native — il C# fa da proxy verso Python.
/// Route suggerita: POST /api/v1/drugs/image
/// </summary>
[ApiController]
[Route("api/v1/drugs")]
public sealed class DrugImageController : ControllerBase
{
    private readonly IDrugImageService _drugImageService;

    public DrugImageController(IDrugImageService drugImageService)
    {
        _drugImageService = drugImageService;
    }

    /// <summary>
    /// Richiesta dall'app dopo scansione AIC.
    /// Aggiungi [Authorize] se le altre route PillApp richiedono JWT.
    /// </summary>
    [HttpPost("image")]
    [ProducesResponseType(typeof(DrugImageResponse), StatusCodes.Status200OK)]
    public async Task<ActionResult<DrugImageResponse>> GetPackageImage(
        [FromBody] DrugImageApiRequest body,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(body.Aic) || string.IsNullOrWhiteSpace(body.Name))
            return BadRequest(new { message = "aic e name sono obbligatori" });

        var pythonRequest = new DrugInfoRequest
        {
            Aic = body.Aic.Trim(),
            Name = body.Name.Trim(),
            Dosage = body.Dosage,
            PharmaceuticalForm = body.PharmaceuticalForm,
            PackageQuantity = body.PackageQuantity,
            MarketingAuthorizationHolder = body.MarketingAuthorizationHolder,
        };

        var result = await _drugImageService.FetchPackageImageAsync(
            pythonRequest,
            cancellationToken);

        // 200 anche se success=false: l'app gestisce il placeholder
        return Ok(result);
    }
}

/// <summary>
/// Body dall'app RN (camelCase standard .NET).
/// </summary>
public sealed class DrugImageApiRequest
{
    public required string Aic { get; init; }
    public required string Name { get; init; }
    public string? Dosage { get; init; }
    public string? PharmaceuticalForm { get; init; }
    public string? PackageQuantity { get; init; }
    public string? MarketingAuthorizationHolder { get; init; }
}
