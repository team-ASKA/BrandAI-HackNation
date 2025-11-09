document.addEventListener('DOMContentLoaded', () => {
    const uploadButton = document.getElementById('upload-button');
    const imageUpload = document.getElementById('image-upload');
    const submitButton = document.getElementById('submit-button');
    const regenerateButton = document.getElementById('regenerate-button');
    const fileNameDisplay = document.getElementById('file-name');
    const uploadArea = document.querySelector('.upload-area');

    let imageFile = null;
    let currentRefinementPlan = null;

    // Handle file selection via button
    uploadButton.addEventListener('click', () => imageUpload.click());
    imageUpload.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            handleFile(file);
        }
    });

    // Handle file drag and drop
    uploadArea.addEventListener('dragover', (event) => {
        event.preventDefault();
        uploadArea.classList.add('drag-over');
    });
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });
    uploadArea.addEventListener('drop', (event) => {
        event.preventDefault();
        uploadArea.classList.remove('drag-over');
        const file = event.dataTransfer.files[0];
        if (file) {
            handleFile(file);
        }
    });

    function handleFile(file) {
        if (file && file.type.startsWith('image/')) {
            imageFile = file;
            fileNameDisplay.textContent = file.name;
            submitButton.disabled = false;
        } else {
            imageFile = null;
            fileNameDisplay.textContent = 'Please select a valid image file.';
            submitButton.disabled = true;
        }
    }

    // Handle initial form submission for evaluation
    submitButton.addEventListener('click', async () => {
        if (!imageFile) {
            alert('Please select an image first.');
            return;
        }

        const formData = new FormData();
        formData.append('image', imageFile); 

        showLoadingState();

        try {
            const response = await fetch('/evaluate', { // <-- 1. Call /evaluate
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();
            displayCritiqueResults(data); // <-- 2. Display critique, not final results

        } catch (error) {
            console.error('Error during evaluation API call:', error);
            showErrorState(`An error occurred during evaluation: ${error.message}`);
        }
    });

    // Handle regeneration button click
    regenerateButton.addEventListener('click', async () => {
        if (!currentRefinementPlan) {
            alert('No refinement plan available to generate from.');
            return;
        }

        const regenLoader = document.getElementById('regenerated-image-loader');
        const regenImage = document.getElementById('regenerated-image');
        regenLoader.style.display = 'flex';
        regenImage.style.display = 'none';
        regenerateButton.disabled = true;

        try {
            const response = await fetch('/regenerate', { // <-- 3. Call /regenerate
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ refinement_plan: currentRefinementPlan }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();
            displayRegeneratedImage(data.regenerated_image_url); // <-- 4. Display new image

        } catch (error) {
            console.error('Error during regeneration API call:', error);
            // Optionally show an error message in the regeneration column
        } finally {
            regenLoader.style.display = 'none';
            regenerateButton.disabled = false;
        }
    });


    function showLoadingState() {
        document.getElementById('results-placeholder').style.display = 'none';
        document.getElementById('results-content').style.display = 'none';
        document.getElementById('images-results-section').style.display = 'none';
        document.getElementById('loader').style.display = 'flex';
        regenerateButton.style.display = 'none';
    }

    function showErrorState(message) {
        document.getElementById('loader').style.display = 'none';
        const placeholder = document.getElementById('results-placeholder');
        placeholder.style.display = 'flex';
        placeholder.querySelector('.placeholder-title').textContent = 'Analysis Failed';
        placeholder.querySelector('.placeholder-text').textContent = message;
    }

    function displayCritiqueResults(data) {
        document.getElementById('loader').style.display = 'none';
        document.getElementById('results-placeholder').style.display = 'none';
        
        const imagesSection = document.getElementById('images-results-section');
        const resultsContent = document.getElementById('results-content');
        imagesSection.style.display = 'block';
        resultsContent.style.display = 'block';

        // Store the refinement plan for the next step
        currentRefinementPlan = data.refinement_plan;

        // Populate original image
        document.getElementById('original-image').src = data.original_image;
        
        // Show placeholder for regenerated image
        const regenImage = document.getElementById('regenerated-image');
        const regenPlaceholder = document.getElementById('regenerated-image-placeholder');
        regenImage.style.display = 'none';
        regenPlaceholder.style.display = 'flex';


        // Populate header
        document.getElementById('results-title').textContent = `Critique for ${data.brand_name}`;
        const overallScoreEl = document.getElementById('overall-score');
        const overallScore = data.scorecard.overall_score;
        overallScoreEl.textContent = (overallScore * 100).toFixed(0);
        overallScoreEl.style.backgroundColor = getScoreColor(overallScore);

        // Populate scorecard
        const scorecardContainer = document.getElementById('scorecard-container');
        scorecardContainer.innerHTML = ''; // Clear previous results
        const scorecardData = {
            "Brand Alignment": data.scorecard.brand_alignment,
            "Visual Quality": data.scorecard.visual_quality,
            "Message Clarity": data.scorecard.message_clarity,
            "Safety & Ethics": data.scorecard.safety_ethics,
        };

        for (const [title, details] of Object.entries(scorecardData)) {
            const card = document.createElement('div');
            card.className = 'score-card';
            
            const scoreValue = details.score;
            const scoreColor = getScoreColor(scoreValue);

            card.innerHTML = `
                <div class="score-card-header">
                    <h4 class="score-card-title">${title}</h4>
                    <div class="score-badge" style="background-color: ${scoreColor};">${(scoreValue * 100).toFixed(0)}</div>
                </div>
                <p class="score-card-feedback">${details.feedback}</p>
            `;
            scorecardContainer.appendChild(card);
        }

        // Populate strengths
        const strengthsList = document.getElementById('strengths-list');
        strengthsList.innerHTML = '';
        if (data.scorecard.strengths && data.scorecard.strengths.length > 0) {
            data.scorecard.strengths.forEach(strength => {
                const li = document.createElement('li');
                li.textContent = strength;
                strengthsList.appendChild(li);
            });
        } else {
            strengthsList.innerHTML = '<li>No specific strengths identified.</li>';
        }

        // Populate refinement plan
        const refinementPlanText = document.getElementById('refinement-plan-text');
        refinementPlanText.textContent = data.refinement_plan;

        // Show the regenerate button
        regenerateButton.style.display = 'block';
    }

    function displayRegeneratedImage(imageUrl) {
        const regenImage = document.getElementById('regenerated-image');
        const regenPlaceholder = document.getElementById('regenerated-image-placeholder');
        const regenLoader = document.getElementById('regenerated-image-loader');
        
        regenLoader.style.display = 'none';
        regenPlaceholder.style.display = 'none';
        regenImage.src = imageUrl;
        regenImage.style.display = 'block';
    }

    function getScoreColor(score) {
        if (score >= 0.8) return 'var(--success-color)';
        if (score >= 0.5) return 'var(--warning-color)';
        return 'var(--danger-color)';
    }
});