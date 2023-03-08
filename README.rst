=========================
 Unified Runtime Publish
=========================


The unified-runtime branch in this repo contains the HTML for the
doc. To make changes, follow the typical GitHub workflow of forking
this repo, updating the HTML files, and submitting a PR against the
unified-runtime branch in this repo. Update the version of the doc in
the `CI script`_.

When the PR is submitted, the CI will publish the doc at
https://spec.pre.oneapi.com/unified-runtime/latest/index.html. When
the PR is merged, the CI publishes the doc at
https://spec.oneapi.com/unified-runtime/latest/index.html.

.. _`CI script`: https://github.com/intel-sandbox/personal.rscohn1.oneapi-doc-publish/blob/unified-runtime/.github/workflows/ci.yml#L13
